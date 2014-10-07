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

import logging

import tornado.concurrent
import tornado.gen
import tornado.ioloop

import common.protocol

class Proxy:
	def __init__(self, wrapped_stream, raw_stream):
		self.wrapped_stream = wrapped_stream
		self.raw_stream = raw_stream
		self.finish_future = tornado.concurrent.Future()

	@tornado.gen.coroutine
	def read_wrapped(self):
		logging.debug('Proxy.read_wrapped')
		try:
			while True:
				package = yield common.protocol.package.read(self.wrapped_stream)
				if isinstance(package, common.protocol.payload):
					payload = package.payload
					logging.debug('WRAPPED -> RAW: {}'.format(repr(payload)))
					yield self.raw_stream.write(payload)
				elif isinstance(package, common.protocol.disconnect):
					logging.debug('Disconnection of tunneled client, stopping proxy')
					self.raw_stream.close()
					self.finish_future.set_result(True)
				else:
					raise Exception('Unexpected package received: {}'.format(package))
		except Exception as e:
			try:
				yield common.protocol.disconnect().write(self.wrapped_stream)
				self.finish_future.set_exception(e)
			except Exception as e:
				self.finish_future.set_exception(e)

	@tornado.gen.coroutine
	def read_raw(self):
		logging.debug('Proxy.read_raw')
		try:
			while True:
				payload = yield self.raw_stream.read_bytes(2**24, partial=True)
				logging.debug('RAW -> WRAPPED: {}'.format(repr(payload)))
				yield common.protocol.payload(payload).write(self.wrapped_stream)
		except Exception as e:
			if not self.raw_stream.closed():
				self.raw_stream.close()
			try:
				yield common.protocol.disconnect().write(self.wrapped_stream)
				self.finish_future.set_exception(e)
			except Exception as e:
				self.finish_future.set_exception(e)

	def run(self):
		logging.debug('Proxy.run')

		tornado.ioloop.IOLoop.instance().add_callback(self.read_wrapped)
		tornado.ioloop.IOLoop.instance().add_callback(self.read_raw)

		return self.finish_future