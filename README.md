About
=====

NATadm stands from "NAT administrator" - allows to connect directly to machines that are located behind NAT. This is done by proxying all data through
external server.

Two parts of the system:

 * Client - part that is installed on administrated machine. In given intervals, it connects with server to check if there are waiting requests for connection. If yes, it establishes bridge between local service (e.g. local SSH port) and server side.

 * Server - installed on publicly available machine (e.g. system with public IP address). It receives requests for connection, waits for clients, and provides public port, which is routed internally to port opened on client.


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
 * ```control_port = 12346``` - port, that will be used for administrator to connect to.
 * ```control_server_certificate = ('../certs/control.crt.pem', '../certs/control.key.pem')``` - certificate, that will be presented for administrator.
 * ```control_client_ca = '../certs/control.ca.pem'``` - CA, that will be used to identify administrator (s/he must provide client's certificate)
 * ```communication_port = 12345``` - port, that will be used by clients. Must be public
 * ```communication_server_certificate = ('../certs/communication.crt.pem',    '../certs/communication.key.pem')``` - certificate, that will be presented for clients.

4. *Optional:* Make server to start automatically with the machine. If you skip this step, you have to run server manually before making any connection.

5. Use any SSL command line client (e.g. *OpenSSL's s_client*). Connect with your server's machine control port. You CAN verify certificate provided from server (the one passed to ```control_server_certificate``` configuration option). You MUST provide client-side certificate, that will be verified by server using CA (the one passed to ```control_client_ca``` configuration option).

6. Enter command ```WAITFOR <client name> <client port> <server port>```. ```<client name>``` should be replaced by identifier of the client (the one passed to client's ```name``` configuration option), that you would like to connect with. ```<client port>``` is the number of TCP port that you would like to connect to. This port must be open on client machine, and some service should listen on it. ```<server port>``` is arbitrary port number, that will be opened on your server. After entering a command and getting confirmation message, you can close control connection.

7. Connect with your server, on TCP ```<server port>``` (the one passed in point 6). If port is closed, you must wait at most client's ```interval``` until it becomes available.

You should use client that is acceptable by service, that is listening on ```<client port>``` (for example, if you have SSH server listening on ```<client port>```, you should connect to ```<server port>``` with SSH client). Your client should behave as like communicating directly with client machine.


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
