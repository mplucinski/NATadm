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

import io
import logging
import ssl

import tornado.iostream
import tornado.netutil

def ssl_options(certfile, keyfile, cacerts):
	context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
	context.options |= ssl.OP_NO_SSLv2
	context.options |= ssl.OP_NO_SSLv3
	context.load_cert_chain(certfile, keyfile)
	context.verify_mode = ssl.CERT_REQUIRED
	context.load_verify_locations(cacerts)
	context.verify_flags = ssl.VERIFY_CRL_CHECK_CHAIN

class FileIOStream(tornado.iostream.BaseIOStream):
	def __init__(self, file, *args, **kwargs):
		super(FileIOStream, self).__init__(*args, **kwargs)
		logging.debug('FileIOStream.__init__')
		self.file = file

	def fileno(self):
		logging.debug('FileIOStream.fileno')
		return self.file.fileno()

	def close_fd(self):
		logging.debug('FileIOStream.close_fd')
		self.file.close()
		self.file = None

	def write_to_fd(self, data):
		logging.debug('FileIOStream.write_to_fd')
		return self.file.write(data)

	def read_from_fd(self):
		logging.debug('FileIOStream.read_from_fd')
		chunk = self.file.read(self.read_chunk_size)
		if not chunk:
			self.close()
			return None
		return chunk

