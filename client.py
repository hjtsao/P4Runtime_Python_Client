
# Copyright 2013-present Barefoot Networks, Inc.
# Copyright 2018-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import Queue
import argparse
import json
import logging
import os
import re
import struct
import subprocess
import sys
import threading
import datetime
from collections import OrderedDict
import time
from StringIO import StringIO
from collections import Counter
from functools import wraps, partial
from unittest import SkipTest

import google.protobuf.text_format
import grpc
from p4.tmp import p4config_pb2
from p4.v1 import p4runtime_pb2

from basic import P4RuntimeClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pi_client")


def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)


def warn(msg, *args, **kwargs):
    logger.warn(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def main():
    parser = argparse.ArgumentParser(
        description="Compile the provided P4 program and run PTF tests on it")
    parser.add_argument('--device',
                        help='Target device',
                        type=str, action="store", required=True,
                        choices=['tofino', 'bmv2', 'stratum-bmv2'])
    parser.add_argument('--p4info',
                        help='Location of p4info proto in text format',
                        type=str, action="store", required=True, 
                        default='/home/sdn/onos/pipelines/basic/src/main/resources/p4c-out/bmv2/basic.p4info')
    parser.add_argument('--grpc-addr',
                        help='Address to use to connect to P4 Runtime server',
                        type=str, default='localhost:50051')
    parser.add_argument('--device-id',
                        help='Device id for device under test',
                        type=int, default=1)
    parser.add_argument('--cpu-port',
                        help='CPU port ID of device under test',
                        type=int, required=True)
    parser.add_argument('--skip-config',
                        help='Assume a device with pipeline already configured',
                        action="store_true", default=False)
    args, unknown_args = parser.parse_known_args()

    # device = args.device

    if not os.path.exists(args.p4info):
        error("P4Info file {} not found".format(args.p4info))
        sys.exit(1)

    # grpc_port = args.grpc_addr.split(':')[1]

    try:
	print "Try to connect to P4Runtime Server"
        s1 = P4RuntimeClient(grpc_addr = args.grpc_addr, device_id = args.device_id, cpu_port = args.cpu_port, p4info_path = args.p4info)
	was_packetin = 0
	wrote = 0
	while 1:
		s1.packetin_rdy.wait()
		print(datetime.datetime.now(), "Looking queue")
		packetin = s1.get_packet_in()
		if was_packetin and not packetin and not wrote:
			# Set flow rule to tableNCS
            		print "Insert entry"
            		req = s1.get_new_write_request()
            		s1.push_update_add_entry_to_action(
            		    req,
            		    "ingress.tableNCS_control.tableNCS",
            		    [s1.Ternary("hdr.ipv4.protocol", '\x01', '\xff')],
            		    #"_drop", [], 70000)
			    # Change the action to "send_to_cpu, no need the parameter array"
            		    "tableNCS_control.set_egress_port", [("port", b'\x00\x03')], 100)
            		s1.write_request(req)
			wrote = 1			
		was_packetin = 0
		if packetin:
			was_packetin = 1
			# Print Packet from CPU_PORT of Switch
			print("Got a packet.")
			print " ".join("{:02x}".format(ord(c)) for c in packetin.payload)
			
			# Print metadatas:
			# 	1. packet_in switch port (9 bits)
			#	2. padding (7 bits)
			for metadata_ in packetin.metadata:
				print " ".join("{:02x}".format(ord(c)) for c in metadata_.value)
		s1.packetin_rdy.clear();
		time.sleep(1)

    except Exception:
        raise
        s1.tearDown()

    except KeyboardInterrupt:
        s1.tearDown()


if __name__ == '__main__':
    main()
