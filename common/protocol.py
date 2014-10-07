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
import os
import pickle
import sys
import unittest

import tornado.gen

sys.path.append(os.path.join(os.getcwd(), '..'))

import common.utils

DEFAULT_VERSION = 1
MAX_VERSION = 1

class package:
	@staticmethod
	@tornado.gen.coroutine
	def read(stream):
		if isinstance(stream, bytes):
			stream = common.utils.FileIOStream(io.BytesIO(stream))
		length = []
		while True:
			b = (yield stream.read_bytes(1))[0]
			length.append(int(b))
			if b & 0x80:
				break;
		length = package._decode_length(length)
		logging.debug('Reading package of {} B'.format(length))
		pkg = yield stream.read_bytes(length)
		return pickle.loads(pkg)

	@tornado.gen.coroutine
	def write(self, stream):
		b = pickle.dumps(self)
		logging.debug('Writing package of {} B'.format(len(b)))
		length = package._encode_length(len(b))
		yield stream.write(length)
		yield stream.write(b)

	@staticmethod
	def _encode_length(length):
		output = []
		while True:
			byte = length & 0x7F
			length >>= 7;

			if length == 0:
				byte |= 0x80

			output.append(byte)

			if length == 0:
				break
		return bytes(output)

	@staticmethod
	def _decode_length(length):
		output = 0
		assert length[-1] & 0x80
		for i in range(len(length)-1, -1, -1):
			byte = length[i]
			if length[i] & 0x80:
				byte &= ~0x80
			output <<= 7
			output |= byte
		return output

class hello(package):
	def __init__(self, name, protocol_version = DEFAULT_VERSION):
		self.name = name
		self.protocol_version = protocol_version

	def check_protocol_version(self):
		if self.protocol_version > MAX_VERSION:
			raise Exception('Too new protocol version: {}'.format(self.protocol_version))

class not_interested(package):
	pass

class create_tunnel(package):
	def __init__(self, port):
		self.port = port

class connect(package):
	pass

class disconnect(package):
	pass

class payload(package):
	def __init__(self, payload):
		self.payload = payload

class error(package):
	def __init__(self, message):
		self.message = message

class TestEncodeDecodeLength(unittest.TestCase):
	def test_encode_decode(self):
		for original in range(1, 2**24):
			print('Checking {}'.format(original))
			encoded = package._encode_length(original)
			print('   encoded: {}'.format(repr(encoded)))
			decoded = package._decode_length(encoded)
			self.assertEqual(original, decoded)

if __name__ == '__main__':
	unittest.main()