#!/bin/python3

import subprocess
import sys
import time
import threading
import queue
from termcolor import colored

# Print the banner
banner_lines = [
    '.------..------..------..------..------..------..------.',
    '|J.--. ||U.--. ||G.--. ||G.--. ||L.--. ||E.--. ||R.--. |',
    '| :(): || (\/) || :/\: || :/\: || :/\: || (\/) || :(): |',
    '| ()() || :\/: || :\/: || :\/: || (__) || :\/: || ()() |',
    "| '--'J|| '--'U|| '--'G|| '--'G|| '--'L|| '--'E|| '--'R|",
    "`------'`------'`------'`------'`------'`------'`------'",
    '\nBy DownwithmyDaemons'
]
for line in banner_lines:
    print(colored(line, 'red'))

# ANSI escape codes for colors
COLOR_RESET = "\033[0m"
COLOR_YELLOW = "\033[33m"
COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"

class NetcatListener:
    def __init__(self, port):
        self.port = port
        self.process = None
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        self.running = True

    def start(self):
        try:
            command = ['nc', '-l', '-p', str(self.port)]
            print(f"Starting netcat listener on port {self.port}...")
            self.process = subprocess.Popen(command,
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            text=True,
                                            bufsize=1,
                                            universal_newlines=True)
            print(f"Netcat listener started on port {self.port} with PID {self.process.pid}")

            # Start threads to read stdout and stderr
            threading.Thread(target=self._read_stdout, daemon=True).start()
            threading.Thread(target=self._read_stderr, daemon=True).start()

        except FileNotFoundError:
            print("Netcat (nc) is not installed. Please install it and try again.", file=sys.stderr)
        except Exception as e:
            print(f"Error starting netcat: {e}", file=sys.stderr)

    def _read_stdout(self):
        while self.running:
            output = self.process.stdout.readline()
            if output:
                self.stdout_queue.put(output)
            if self.process.poll() is not None and self.process.stdout.closed:
                break

    def _read_stderr(self):
        while self.running:
            error = self.process.stderr.readline()
            if error:
                self.stderr_queue.put(error)
            if self.process.poll() is not None and self.process.stderr.closed:
                break

    def stop(self):
        if self.process:
            print(f"Stopping netcat listener on port {self.port}...")
            self.running = False
            self.process.terminate()
            self.process.wait()
            print(f"Netcat listener stopped on port {self.port}.")
        else:
            print(f"Netcat listener on port {self.port} is not running.")

    def send_data(self, data):
        if self.process:
            self.process.stdin.write(data + '\n')
            self.process.stdin.flush()

    def receive_data(self):
        output = ""
        while not self.stdout_queue.empty():
            output += self.stdout_queue.get()
        return output.strip()

class ConnectionManager:
    def __init__(self):
        self.connections = {}
        self.selected_port = None

    def add_connection(self, port):
        if port not in self.connections:
            listener = NetcatListener(port)
            listener.start()
            self.connections[port] = listener
        else:
            print(f"Connection on port {port} already exists.")

    def remove_connection(self, port):
        if port in self.connections:
            self.connections[port].stop()
            del self.connections[port]
        else:
            print(f"No connection on port {port} to remove.")

    def list_connections(self):
        return list(self.connections.keys())

    def select_connection(self, port):
        if port in self.connections:
            self.selected_port = port
            print(f"Selected connection on port {self.selected_port}.")
        else:
            print(f"No connection on port {port}.")

    def send_command(self, command):
        if self.selected_port in self.connections:
            self.connections[self.selected_port].send_data(command)
            time.sleep(0.5)  # Give some time for the command to execute
            response = self.connections[self.selected_port].receive_data()
            return response
        else:
            print("No connection selected.")
            return None

    def stop_all(self):
        for port in self.connections.keys():
            self.remove_connection(port)

def print_help():
    print(COLOR_YELLOW + "\nAvailable commands:")
    print("1. add <port> - Add a new netcat listener on the specified port.")
    print("2. remove <port> - Remove the netcat listener on the specified port.")
    print("3. list - List all active connections.")
    print("4. select <port> - Select a connection to interact with.")
    print("5. send <command> - Send a command to the selected connection.")
    print("6. stop - Stop all connections and exit.")
    print("7. help - Display this help message." + COLOR_RESET)

if __name__ == "__main__":
    manager = ConnectionManager()

    try:
        print_help()  # Print the help message when the script starts

        while True:
            # Display output from the selected connection if any
            if manager.selected_port:
                response = manager.connections[manager.selected_port].receive_data()
                if response:
                    print(f"\nReceived from port {manager.selected_port}:\n{response}")

            # Display the port number if selected, otherwise just the command prompt
            if manager.selected_port:
                print(COLOR_RED + f"\n[Port {manager.selected_port}]" + COLOR_RESET)
                
            # Get user input with a green prompt
            command = input(COLOR_GREEN + "Enter command: " + COLOR_RESET).strip()

            if command.startswith("add "):
                _, port = command.split()
                port = int(port)
                manager.add_connection(port)

            elif command.startswith("remove "):
                _, port = command.split()
                port = int(port)
                manager.remove_connection(port)

            elif command == "list":
                connections = manager.list_connections()
                if connections:
                    print("Active connections:", connections)
                else:
                    print("No active connections.")

            elif command.startswith("select "):
                _, port = command.split()
                port = int(port)
                manager.select_connection(port)

            elif command.startswith("send "):
                if manager.selected_port is not None:
                    _, cmd = command.split(maxsplit=1)
                    response = manager.send_command(cmd)
                    print(f"Sent to port {manager.selected_port}:\n{cmd}")
                    print(f"Received from port {manager.selected_port}:\n{response}")
                else:
                    print("No connection selected. Use 'select <port>' to select a connection.")

            elif command == "stop":
                manager.stop_all()
                break

            elif command == "help":
                print_help()

            else:
                print("Unknown command. Please try again.")

    except KeyboardInterrupt:
        print("\nInterrupt received, stopping all connections...")

    finally:
        manager.stop_all()
