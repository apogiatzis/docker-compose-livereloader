import logging
import docker
import threading
import time
import platform

from os import environ
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver


logging.basicConfig(
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger("reloader")


class Reloader(object):
    def __init__(self):
        self.init_docker()
        self.last_reload_thread = None
        self.reload_dirs = self.get_target_dirs()
        self.reload_delay = float(environ.get("RELOAD_DELAY", 1.5))
        self.restart_timeout = int(environ.get("RESTART_TIMEOUT", 10))
        self.reload_container = environ.get("RELOAD_CONTAINER")
        self.observer_type = int(environ.get("OBSERVER_TYPE",0))
        self.must_run = int(environ.get("MUST_RUN", 1))

    @staticmethod
    def _get_own_container_id():
        """
        Identifies reloader own container id, in cases we want to run multiple reloaders.
        """
        return platform.node()

    def event_handler_factory(
        self, *args, patterns=["*"], ignore_directories=True, **kwargs
    ):
        event_handler = PatternMatchingEventHandler(
            *args, patterns=patterns, ignore_directories=ignore_directories, **kwargs
        )

        def on_any_event_callback(event):
            """
            Callback to react on any watchdog filesystem event.
            """
            containers = self.get_target_containers()
            if containers:
                logger.info(event)
                logger.info(f"Scheduling reloading of containers")
                self.scheduled_reload(containers)

        event_handler.on_any_event = on_any_event_callback
        return event_handler

    def init_docker(self):
        """
        Initializes docker client with binded docker socket.
        """
        self.client = docker.DockerClient(base_url="unix://var/run/docker.sock")

    def get_target_dirs(self):
        """
        Returns a the target directory to be monitored in this order:
            1. If the RELOAD_DIR environment variable is set, uses that.
            2. Otherwise it attempts to derive the directory from mounted directories on the container
        """
        dirs = environ.get("RELOAD_DIR", None)
        if dirs is not None:
            dirs = [x.strip() for x in dirs.split(",")]
            return dirs

        container = self.client.containers.get(container_id=self._get_own_container_id())

        dirs_to_watch = []
        for mount in container.attrs["Mounts"]:
            if (
                "/var/run/docker.sock" not in mount["Destination"]
                and "/reloader" not in mount["Destination"]
            ):
                logger.info(f'Watching directory: {mount["Destination"]}')
                dirs_to_watch.append(mount["Destination"])

        return dirs_to_watch if dirs_to_watch else None

    def get_target_containers(self):
        """
        Returns a docker container instance if exists, based on the RELOAD_CONTAINER
        environment variable.
        Enforces exact match for name, by using regex ^/nRELOAD_CONTAINER$
        To target multiple reload targets, RELOAD_LABEL is used.
        """
        container = self.client.containers.list(filters={"name": f"^/{self.reload_container}$"})

        by_name = [container[0]] if container else []

        by_labels = []
        label = environ.get("RELOAD_LABEL", None)
        if label:
            if self.must_run == 1:
                by_labels = self.client.containers.list(
                    filters={"label": label, "status": "running"}
                )
            else:
                by_labels = self.client.containers.list(
                    filters={"label": label}
                )
                by_labels.extend(self.client.containers.list(
                    filters={"label": label, "status": "exited"}
                ))

        return list(set(by_name + by_labels))

    def scheduled_reload(self, containers):
        """
        Schedules a thread to reload the container based on the given RELOAD DELAY.
        It overwrites any previously scheduled reloading threads.
        """

        def containers_reload():
            """
            Restarts given containers and reports any errors.
            """
            try:
                for container in containers:
                    logger.info("Reloading container: {0}".format(container.name))
                    container.restart(timeout=self.restart_timeout)
            except Exception as e:
                logger.error("Something went wrong while reloading: ")
                logger.error(e)

        # if containers:
        if self.last_reload_thread:
            self.last_reload_thread.cancel()
        del self.last_reload_thread
        self.last_reload_thread = threading.Timer(self.reload_delay, containers_reload)
        self.last_reload_thread.start()

    def start(self):
        """
        Runs watchdog process to monitor file changes and reload container
        """

        if self.observer_type == 0:
            observer = Observer()
        elif self.observer_type == 1:
            observer = PollingObserver()

        if self.reload_dirs:
            for a_dir in self.reload_dirs:
                observer.schedule(self.event_handler_factory(), a_dir, recursive=True)
            observer.start()
        else:
            logger.error("Did not find any source code paths to monitor!!")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
