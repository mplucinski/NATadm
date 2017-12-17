#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2014 Mariusz Pluciński
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import collections
import logging
import os.path
import shlex
import ssl
import sys
import tempfile

current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
sys.path.insert(0, os.path.dirname(current_dir))

import tornado.gen
import tornado.ioloop
import tornado.options
import tornado.tcpclient
import tornado.tcpserver

import common.protocol
import common.proxy
import common.utils

CONFIG_FILE = 'NATadm_server.conf'

common.utils.reformat_logger('SERVER')

#tornado.options.define('control_port', type=int)
#tornado.options.define('control_server_certificate', type=tuple)
#tornado.options.define('control_client_ca', type=str)

tornado.options.define('communication_port', type=int)
tornado.options.define('communication_server_certificate', type=tuple)
tornado.options.define('communication_client_ca', type=str)

tornado.options.define('services', type=dict)

tornado.options.define('config_file', type=str)

tornado.options.parse_command_line(None, False)

config_file = tornado.options.options.config_file or CONFIG_FILE

if len(config_file) != 0:
	if not os.path.exists(config_file):
		raise Exception('Not found: {!r}'.format(config_file))
	tornado.options.parse_config_file(config_file, False)

tornado.options.options.run_parse_callbacks()

COMMAND_WAITFOR = 'WAITFOR'
COMMAND_NOWAIT = 'NOWAIT'
COMMAND_EXIT = 'EXIT'
COMMAND_KILL = 'KILL'

class Server(tornado.tcpserver.TCPServer):
	def __init__(self, *args, **kwargs):
		super(Server, self).__init__(*args, **kwargs)
		self.requests_table = dict()

	@tornado.gen.coroutine
	def handle_stream(self, stream, address):
		try:
			logging.debug('Client connected')
			package = yield common.protocol.package.read(stream)
			if not isinstance(package, common.protocol.hello):
				raise Exception('Invalid package received, HELLO expected')

			package.check_protocol_version()

			logging.debug('Client name: \"{}\"'.format(package.name))
			if package.name in self.requests_table:
				(client_port, server_port, orig_client_address) = self.requests_table[package.name]
				del self.requests_table[package.name]
				yield common.protocol.create_tunnel(client_port).write(stream)
				if isinstance(server_port, ForwardServer):
					logging.info('Client \"{}\" will forward it\'s port {} to awaiting connection'.format(package.name, client_port))
					server_stream = server_port.awaiting_stream
					server_address = server_port.awaiting_address
				else:
					logging.info('Client \"{}\" will forward it\'s port {} to local {}'.format(package.name, client_port, server_port))
					forward = ForwardServer(self)
					forward.listen(server_port)
					logging.info('Waiting for connections on {}'.format(server_port))
					(server_stream, server_address) = yield forward.accept()
				logging.info('Incoming connection to be tunneled from {}'.format(server_address))
				yield common.protocol.connect(orig_client_address).write(stream)

				proxy = common.proxy.Proxy('NATadm:{}:{}'.format(package.name, client_port), stream, orig_client_address, server_stream)
				yield proxy.run()

			else:
				logging.info('Client "{}" connected, but no pending requests for it - disconnecting'.format(package.name))
				yield common.protocol.not_interested().write(stream)
		except Exception as e:
			logging.exception(e)
			if not stream.closed():
				yield common.protocol.error(str(e)).write(stream)
		finally:
			if not stream.closed():
				stream.close()

class ForwardServer(tornado.tcpserver.TCPServer):
	def __init__(self, server, *args, **kwargs):
		super(ForwardServer, self).__init__(*args, **kwargs)
		self.server = server
		self.accept_future = tornado.concurrent.Future()
		self.target_client = None
		self.target_port = None
		self.awaiting_stream = None
		self.awaiting_address = None

	@tornado.gen.coroutine
	def set_permanent_service(self, client, port):
		self.target_client = client
		self.target_port = port

	def accept(self):
		return self.accept_future

	@tornado.gen.coroutine
	def handle_stream(self, stream, address):
		logging.debug('Incoming connection to forward server from {}'.format(address))
		if self.target_client is None and self.target_port is None:
			self.accept_future.set_result((stream, address))
		else:
			logging.info('User connected from {}, will forward to {}:{}'.format(
				address, self.target_client, self.target_port
			))
			self.server.requests_table[self.target_client] = (self.target_port, self, address)
			self.awaiting_stream = stream
			self.awaiting_address = address

#class ControlServer(tornado.tcpserver.TCPServer):
#	def __init__(self, server, *args, **kwargs):
#		super(ControlServer, self).__init__(*args, **kwargs)
#		self.server = server
#
#	@tornado.gen.coroutine
#	def message(self, stream, s):
#		logging.info('Response: \"{}\"'.format(s))
#		yield stream.write((s+'\n').encode('utf-8'))
#
#	@tornado.gen.coroutine
#	def handle_stream(self, stream, address):
#		try:
#			logging.info('Controller connected')
#			yield self.message(stream, 'NATadm_server')
#			logging.info('Connected peer\'s certificate: '+repr(stream.socket.getpeercert()))
#			while True:
#				line = yield stream.read_until(b'\n')
#				line = line.decode('utf-8').strip()
#				logging.debug('Command: "{}"'.format(str(line)))
#
#				line = shlex.split(line)
#				if line[0] == COMMAND_WAITFOR:
#					client = line[1]
#					client_port = line[2]
#					server_port = line[3]
#					if client in self.server.requests_table:
#						yield self.message(stream, 'Client \"{}\" already exists in requests table'.format(client))
#					else:
#						self.server.requests_table[client] = (client_port, server_port)
#						yield self.message(stream, 'Client \"{}\" is added to requests table with port {} forwarding to {}'.format(client, client_port, server_port))
#				elif line[0] == COMMAND_NOWAIT:
#					client = line[1]
#					if not client in self.server.requests_table:
#						yield self.message(stream, 'Client \"{}\" does not exist in requests table'.format(client))
#					else:
#						del self.server.requests_table[client]
#						yield self.message(stream, 'Client \"{}\" is removed from requests table'.format(client))
#				elif line[0] == COMMAND_EXIT:
#					yield self.message(stream, 'Exiting')
#					stream.close()
#					return
#				elif line[0] == COMMAND_KILL:
#					yield self.message(stream, 'Killing server')
#					stream.close()
#					tornado.ioloop.IOLoop.instance().stop()
#					return
#				else:
#					yield self.message(stream, 'Unknown command')
#		except Exception as e:
#			logging.exception(e)
#			if not stream.closed():
#				yield self.message(stream, 'Command processing error')
#		finally:
#			if not stream.closed():
#				stream.close()

def main():
	logging.info('=== NATadm server (protocol version: {}) ==='.format(common.protocol.MAX_VERSION))
	io_loop = tornado.ioloop.IOLoop.instance()

	server = Server(ssl_options=common.utils.ssl_options(
		certfile=tornado.options.options.communication_server_certificate[0],
		keyfile=tornado.options.options.communication_server_certificate[1],
		cacerts=tornado.options.options.communication_client_ca
	))
	logging.info('Listening on port {} ...'.format(tornado.options.options.communication_port))
	server.listen(tornado.options.options.communication_port)

#	control_server = ControlServer(server, ssl_options=common.utils.ssl_options(
#		certfile=tornado.options.options.control_server_certificate[0],
#		keyfile=tornado.options.options.control_server_certificate[1],
#		cacerts=tornado.options.options.control_client_ca
#	))

#	logging.info('Listening on control interface on {} ...'.format(
#		tornado.options.options.control_port
#	))
#	control_server.listen(
#		tornado.options.options.control_port
#	)

	for port, service in tornado.options.options.services.items():
		logging.info('Listening on port {} for connections to forward to {}:{}'.format(port, service['client'], service['port']))

		forward_server = ForwardServer(server)
		forward_server.set_permanent_service(service['client'], service['port'])
		forward_server.listen(port)

	io_loop.start()

if __name__ == '__main__':
	main()
