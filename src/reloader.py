import logging
import docker
import threading
import time

from os import environ
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

logger = logging.getLogger("reloader")

RELOAD_DELAY = float(environ.get("RELOAD_DELAY", 1.5))
RELOAD_CONTAINER = environ.get("RELOAD_CONTAINER")
RELOAD_DIR = environ.get("RELOAD_DIR")

class Reloader(object):

    def __init__(self):
        self.init_docker()
        self.last_reload_thread = None

    def event_handler_factory(self, *args, patterns=["*"], ignore_directories=True, **kwargs):
        event_handler = PatternMatchingEventHandler(
            *args,
            patterns=patterns,
            ignore_directories=ignore_directories,
            **kwargs
        )

        def on_any_event_callback(event):
            """
            Callback to react on any wathcdog filesystem event.
            """
            logger.info("Reloading Event: {0}", event)
            self.shcedule_reload(
                self.get_target_container()
            )

        event_handler.on_any_event = on_any_event_callback
        return event_handler

    def init_docker(self):
        """
        Initializes docker client with binded docker socket.
        """
        self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')

    def get_target_dir(self):
        """
        Returns a the target directory to be monitored in this order:
            1. If the RELOAD_DIR environment variable is set, uses that.
            2. Otherwise it attempts to derive the directory from mounted directories on the container
        """
        dir_to_watch = environ.get("RELOAD_DIR", None)
        if dir_to_watch is not None:
            return dir_to_watch

        container = self.client.containers.list(filters={
            "name": "livereloader"
        })[0]
        for mount in container.attrs["Mounts"]:
            if "/var/run/docker.sock" not in mount["Destination"] and "/reloader" not in mount["Destination"]:
                dir_to_watch = mount["Destination"]
        
        return dir_to_watch

    def get_target_container(self):
        """
        Returns a docker container instance if exists, based on the RELOAD_CONTAINER
        environment variable.
        """
        container = self.client.containers.list(filters={
            "name": RELOAD_CONTAINER
        })
        if len(container) == 0:
            raise Exception("Container to reload not found. Have you set RELOAD_CONTAINER variable? (Or is it runnng?)")
        return container[0]

    def shcedule_reload(self, container):
        """
        Schedules a thread to reload the container based on the given RELOAD DELAY.
        It overwrites any previously scheduled reloading threads.
        """
        def container_reload():
            """
            Restarts given container and reports any errors.
            """
            logger.info("Reloading container: {0}".format(container.name))
            try:
                container.restart()
            except Exception as e:
                logger.error("Something went wrong while reloading: ")
                logger.error(e)
        
        if self.last_reload_thread:
            self.last_reload_thread.cancel()
        del self.last_reload_thread
        self.last_reload_thread = threading.Timer(RELOAD_DELAY, container_reload)
        self.last_reload_thread.start()
    
    def start(self):
        """
        Runs watchdog process to monitor file changes and reload container
        """
        observer = Observer()
        observer.schedule(
            self.event_handler_factory(),
            self.get_target_dir(),
            recursive=True
        )
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()