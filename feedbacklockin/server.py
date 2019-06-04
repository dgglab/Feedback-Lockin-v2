'''
Creates a TCP server socket on localhost that can send data to other programs
such as MATLAB. For an overview of how sockets work, see the official python
socket guide: https://docs.python.org/3/howto/sockets.html
'''
from functools import partial
import socket
import time

from PySide2.QtCore import QObject, Signal
from PySide2.QtNetwork import QTcpServer, QHostAddress, QTcpSocket


class Server(QObject):

    send_data = Signal(QTcpSocket)
    set_v = Signal(int, float)
    set_i = Signal(int, float)
    set_ki = Signal(float)
    set_feed = Signal(int, bool)
    autotune = Signal(float)

    def __init__(self, port):
        QObject.__init__(self)
        self._server = QTcpServer()
        self._server.newConnection.connect(self._new_connection)
        self._server.acceptError.connect(self._accept_error)
        if not self._server.listen(QHostAddress.LocalHost, port):
            print(f'Error starting TCP server: {self._server.errorString()}')
        else:
            print(f'Listening on port {self._server.serverPort()}')

    def close(self):
        self._server.close()

    def _new_connection(self):
        conn = self._server.nextPendingConnection()
        conn.disconnected.connect(conn.deleteLater)
        conn.readyRead.connect(partial(self._handle, conn))
        conn.error.connect(self._conn_error)

    def _accept_error(self, err):
        print(f'Error accepting connection: {err}')

    def _conn_error(self, err):
        print(f'Connection error: {err}')

    def _handle(self, conn):
        l = conn.readLine().data().decode('utf-8').strip().split(' ')
        try:
            if l[0] == 'sendData' or l[0] == 'send_data':
                self.send_data.emit(conn)
            elif l[0] == 'setV' or l[0] == 'set_setpoint':
                self.set_v.emit(int(l[1]), float(l[2]))
            elif l[0] == 'setI' or l[0] == 'set_amplitude':
                self.set_i.emit(int(l[1]), float(l[2]))
            elif l[0] == 'setKi' or l[0] == 'set_ki':
                self.set_ki.emit(float(l[1]))
            elif l[0] == 'setFeed' or l[0] == 'set_feedback':
                self.set_feed.emit(int(l[1]), bool(int(l[2])))
            elif l[0] == 'autoTune' or l[0] == 'autotune':
                if len(l) == 2:
                    self.autotune.emit(float(l[1]))
                else:
                    self.autotune.emit(1.0)
            else:
                raise ValueError('command not found')
        except ValueError as e:
            print(f'Bad command {l}: {e}')
        except IndexError as e:
            print(f'Bad command {l}: wrong number of arguments')
