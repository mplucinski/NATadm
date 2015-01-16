About
=====

NATadm stands from "NAT administrator" - allows to connect directly to machines that are located behind NAT. This is done by proxying all data through
external server.

Two parts of the system:

 * Client - part that is installed on administrated machine. In given intervals, it connects with server to check if there are waiting requests for connection. If yes, it establishes bridge between local service (e.g. local SSH port) and server side.

 * Server - installed on publicly available machine (e.g. system with public IP address). It opens ports, waiting for user - after receiving a connection, it waits for connection from needed client. After that, it proxies all the communication between them.

Quick How-to
============

1. Install "client" on target machine. Adjust it's configuration file:
 * ```name = 'foo bar'``` - name that will identify this machine as a connection target. Must be unique in the scope of single server
 * ```remote = ('example.com', 12345)``` - public place, where server will be installed. First element is host name (IP address or DNS name), second is TCP port.
 * ```cafile = '../certs/communication.ca.pem'``` - CA which will be used to identify server. Server's "communication" certificate MUST be verified with this CA, or machines will not be able to communicate.
 * ```interval = 5``` - interval, in seconds, between request checks. Each check requires starting TCP connection, exchanging about 4 packages. Lower values will cause administrator to establish connection faster, higher will reduce network traffic in idle time.
 * ```infinite = True``` - setting to false will cause client to terminate after single requests check. Usually should not be modified.

2. *Optional:* Make client to start automatically with the machine. If you skip this step, you have to run client manually before making any connection.

3. Install server on public machine. Adjust it's configuration file:
 * ```communication_port = 12345``` - port, that will be used by clients. Must be public
 * ```communication_server_certificate = ('../certs/communication.crt.pem',    '../certs/communication.key.pem')``` - certificate, that will be presented for clients.
 * ```services``` - dictionary of services that all proxied by this server. Each element has server's port number as key (the one, that will be one gate of the proxy), and client configuration dictionary as value. Client configuration has two fields: ```name``` - which must match ```name``` field of particular client's own configuration, and ```port```, which is port on client machine (that will be second gate of the proxy). Client's port must be open, and some service should listen on it. but it does not have too be public (honestly, if it is public, using NATadm has no sense).

4. *Optional:* Make server to start automatically with the machine. If you skip this step, you have to run server manually before making any connection.

5. Connect with your server, on TCP port of one of configured services (the one passed in point 6). You will probably not get response from NATted client immediately - in pessimistic case, you will need to wait as many seconds as is configured as client's ```interval```.

You should use client that is acceptable by service, that is listening on ```<client port>``` (for example, if you have SSH server listening on ```<client port>```, you should connect to ```<service port>``` with SSH client). Your client should behave as like communicating directly with client machine.

Note that too big value of ```interval``` may cause client software (or TCP stack) to time out, so set it appropriately.


Requirements
============

Python 3.3 or higher


License
=======

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
