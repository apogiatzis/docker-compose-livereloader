[![forthebadge](https://forthebadge.com/images/badges/built-with-grammas-recipe.svg)](https://forthebadge.com)

# Docker Compose Live Reloader

This docker-compose pattern, aims to provide plug and play live reloading functionality
to docker-compose stacks.

A simple use case scenario for using this is the following:

You have a stack of a web proxy, web server and a database all together containerized
and configured as services in docker-compose for easy deployment. To develop locally,
you make the changes and run `docker-compose up` to inspect what has changed. You
realise that you have do make additional changes but now you need to restart
docker-compose to see them in effect. This procedure is conducted many times in a normal
software develpment lifecycle and in the long term it can be time-consuming and
frustrating. I know that often development servers have auto reloading functionality out
of the box if you mount the code instead of copying it in the docker container, however,
I often find myself needing to have auto reload on commands that do not really have auto
reloading.

With the livereloader docker image you can easily instrument your docker compose service
to be restarted when there are any new file modifications. What is more, the file
watching is configurable such that you can control the delay to wait for reload and the
patterns that reloading should react to (WIP).

Follow the next sections to find more details about this and how to get started using
it.

# Getting Started

It is very simple to get started with the docker-compose live reloader. First things
first, you need to have a docker compose file. The concept is to create a new local
docker-compose file which extends your existing one and just adds one the reloader
service to your stack.

The reloading functionality was written as a separate container such that the changes
required in order to get started using it are minimal. With this in mind, you can easily
separate the local docker-compose files which contain live reloading from automatically
deployed environments.

## How to enable reloading

1. Create a new docker-compose yaml file i.e. `docker-compose-with-reloading.yml` and
   add the following"

```yml
version: '3'

services:

    live-reloader:
        image: apogiatzis/livereloading
        container_name: livereloader
        privileged: true
        environment:
            - RELOAD_CONTAINER=<CONTAINER_NAME>
            - RELOAD_LABEL=<A_DOCKER_CONTAINER_LABEL>
            - RELOAD_DELAY=<DELAY>              # seconds
            - RESTART_TIMEOUT=<TIMEOUT>         # seconds
            - RELOAD_DIR=<DIRS_TO_WATCH>
            - OBSERVER_TYPE=<TYPE>
            - MUST_RUN=<BOOLEAN>
        volumes:
            - "/var/run/docker.sock:/var/run/docker.sock"
            - "<SOURCE CODE DIR>:<DIRECTORY_TO_MOUNT_CODE>"
```

Note that version 3 is only indicative, you can use your own docker compose version
number.

The only required parameters in the above docker-compose service are either the
`RELOAD_CONTAINER` or the `RELOAD_LABEL` variables which give instructions of which
containers are ought to be reloaded. The other variables can be ommited. (More details
in the Configuration section below)

In order for the reloading service to watch for changes you have to mount your source
code directory to a directory in the container. If no `RELOAD_DIR` variable was set,
livereloader automatically watches for changes in that directory. A more explicit path
can be set with `RELOAD_DIR`

Multiple directories can be watched, either by:

- Multiple volume mounts
- Or using a comma separated list (without spaces) asa value of `RELOAD_DIR`. All dirs in `RELOAD_DIR` have to be also mounted on the reloader container, for the watcher to work.

1. Ensure that the code's directory is mounted to your service container as well. (If
   not mounted, reloading will work but code changes will not be applied to restarted
   container)

Assuming that you don't have the source code mounted already and container name is
differently you can add the following in your new docker-compose file to override it.
i.e:

```yml
version: '3'

services:
    ...
    service-name:
        container_name: <SERVICE_CONTAINER_NAME>
        volumes:
            - "<SOURCE CODE DIR>:<DIRECTORY_TO_MOUNT_CODE>"
    ...
```

3. Run your docker compose with live reloading using the following command:

`docker-compose -f docker-compose.yml -f docker-compose-with-reloading.yml up`

## Simple Example

The files for this example are in the `test/` folder of this repository.

Considering that you have the following docker-compose.yml file:

```yml
version: '3'

services:

  test-service:
    image: ubuntu
    volumes:
      - ".:/code"
    working_dir: "/code"
    command: ./command.sh
```

Where `command.sh` is just a simulation of a running service:

```bash
#!/bin/bash
while true ; do
   echo "Alive!" ; sleep 2
   done
```

You should create a new `docker-compose-with-reloading.yml` file and add the following:

```yml
version: '3'

services:
  test-service:
    image: ubuntu
    container_name: test-container-name

  live-reloader:
    image: apogiatzis/livereloading
    container_name: livereloader
    privileged: true
    environment:
      - RELOAD_DELAY=1.5              # seconds
      - RELOAD_CONTAINER=test-container-name
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
      - ".:/code"
```

Run the docker-compose with reloading with this command:

```Shell
docker-compose -f docker-compose.yml -f docker-compose-with-reloading.yml up
```

## A more complicated example - Multiple Reloaders & Routing

In the real world, you will be faced with docker-compose application stacks, with multiple services that perhaps need reload routing, based on changes of multiple mounted directories.

### Monitoring setup

We showcase various scenarios, with a [monitoring stack](test/monitoring/docker-compose.yml) containing the following services:

- `prometheus` with [prometheus.yml](test/monitoring/prometheus/prometheus.yml) configuration file mounted. Exposed on port `9090`.
- A `grafana` with __persistence__, default light theme and pre-loaded dashboards. Configuration mounts are located on [grafana](test/monitoring/grafana) & [grafana-dashboards](test/monitoring/grafana-dashboards). Exposed on port `3000`. We assume this service is used as the "production" grafana instance.
- A test `grafana_barebones` which is __ephemeral__, default dark theme and has no dashboards. The only configuration mount is a [prometheus datasource file](test/monitoring/grafana/datasources/prometheus.yml) that is also shared with `grafana` service. Exposed on port `3001`. We assume this service is used for dashboard tests & POCs.
- Other supporting services and exporters for monitoring a docker daemon such as `influxdb`, `cadvisor` & `node_exporter`

The above services can be better summed up as follows:

```yml
version: '3'
services:

  grafana:
    image: grafana/grafana
    container_name: grafana
    labels:
      reload.grafana: "true"
      single.reload: "true"
    environment:
      - GF_USERS_DEFAULT_THEME=light
      - GF_SECURITY_ADMIN_PASSWORD=grafanaAdmin
      - GF_INSTALL_PLUGINS=grafana-clock-panel, grafana-piechart-panel
      - GF_USERS_ALLOW_SIGN_UP="false"
    expose:
      - 3000
    ports:
      - 3000:3000
    volumes:
      - ./grafana/dashboards/dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml
      - ./grafana/datasources/prometheus.yml:/etc/grafana/provisioning/datasources/prometheus.yml
      - ./grafana-dashboards/docker-dashboards:/mnt/docker-dashboards
      - grafana_data:/var/lib/grafana

  grafana_barebones:
    image: grafana/grafana
    container_name: grafana_barebones
    labels:
      reload.grafana: "true"
    environment:
      - GF_USERS_DEFAULT_THEME=dark
      - GF_SECURITY_ADMIN_PASSWORD=grafanaAdmin
    expose:
      - 3000
    ports:
      - 3001:3000
    volumes:
      - ./grafana/datasources/prometheus.yml:/etc/grafana/provisioning/datasources/prometheus.yml

  prometheus:
    image: prom/prometheus
    container_name: prometheus
    labels:
      single.reload: "true"
    expose:
      - 9090
    ports:
      - 9090:9090
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
```

Full details can be found on [test/monitoring/docker-compose.yml](test/monitoring/docker-compose.yml)
All examples are __runnable.__ At any point you can take a look at the dashboards for `grafana`, `grafana_barebones` & `prometheus` opening your browser at [http://localhost:3000](http://localhost:3000) [http://localhost:3001](http://localhost:3001) and/or [http://localhost:9090](http://localhost:3000)

### Example - Single reloader, single folder - Multiple services

__Scenario:__ Reload both grafanas when there are changes in [datasources shared folder](test/monitoring/grafana/datasources/)

To achieve this we can add a single reloader, mount to it the [datasources shared folder](test/monitoring/grafana/datasources/) and a common `RELOAD_LABEL` to watch.

```yml
services:
  reload_grafanas:
    image: apogiatzis/livereloading
    container_name: reload_grafanas
    privileged: true
    environment:
      - RELOAD_DELAY=2 # seconds
      - RESTART_TIMEOUT=1
      - RELOAD_LABEL=reload.grafana
      - OBSERVER_TYPE=0 # standard = 0, polling = 1
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
      - ./grafana/:/grafana:ro
```

Since `RELOAD_LABEL` `reload.grafana` exists on both `grafana` & `grafana_barebones` services, this allows us tp restart both containers, when a change happens on [test/monitoring/grafana/datasources/prometheus.yml](test/monitoring/grafana/datasources/prometheus.yml) that in theory affects both Grafana datasources.

- To run this example, run the following

```Shell
cd test/monitoring
docker-compose -f docker-compose.yml -f docker-compose-reloaders.yml up -d
```

- To trigger this test reload just issue a save command (e.g. `Ctrl+s` on your editor of choice) on file [test/monitoring/grafana/datasources/prometheus.yml](test/monitoring/grafana/datasources/prometheus.yml) and observe the reloader logs:

```Shell
docker-compose -f docker-compose.yml -f docker-compose-reloaders.yml logs -f reload_grafanas

# Initial output
reload_grafanas              | 21:14:52,31 reloader INFO Watching directory: /grafana

# Trigger output
reload_grafanas              | 21:16:23,117 reloader INFO <FileModifiedEvent: event_type=modified, src_path='/grafana/datasources/prometheus.yml', is_directory=False>
reload_grafanas              | 21:16:23,117 reloader INFO Scheduling reloading of containers
reload_grafanas              | 21:16:23,122 reloader INFO <FileModifiedEvent: event_type=modified, src_path='/grafana/datasources/prometheus.yml', is_directory=False>
reload_grafanas              | 21:16:23,122 reloader INFO Scheduling reloading of containers
reload_grafanas              | 21:16:23,126 reloader INFO <FileClosedEvent: event_type=closed, src_path='/grafana/datasources/prometheus.yml', is_directory=False>
reload_grafanas              | 21:16:23,126 reloader INFO Scheduling reloading of containers
reload_grafanas              | 21:16:25,127 reloader INFO Reloading container: grafana_barebones
reload_grafanas              | 21:16:25,852 reloader INFO Reloading container: grafana
```

As you can observe from the last 2 lines, a single reloader can restart both containers `grafana_barebones` & `grafana` on any change under folder: [test/monitoring/grafana/](test/monitoring/grafana/)

- To fully teardown the example run

```Shell
docker-compose -f docker-compose.yml -f docker-compose-reloaders.yml down -v
```

### Example - Multiple reloaders - Multiple services - 1 to 1

__Scenario Cases:__

- Reload only `grafana` instance when there are changes on file [test/monitoring/grafana-dashboards/docker-dashboards/docker-and-system-monitoring.json](test/monitoring/grafana-dashboards/docker-dashboards/docker-and-system-monitoring.json) since `grafana_barebones` container is not affected by this change.
- Reload `prometheus` when there are changes on file [test/monitoring/prometheus/prometheus.yml](test/monitoring/prometheus/prometheus.yml)

To achieve 1 to 1 combination of reloaders to containers, we use 2 reloader services and explicitly set `RELOAD_CONTAINER` value on each. Keep in mind that `RELOAD_CONTAINER` has to __exactly match__ the targetted container name.

```yml
services:
  reload_grafana_dashboards:
    image: apogiatzis/livereloading
    container_name: reload_grafana_dashboards
    privileged: true
    environment:
      - RELOAD_DELAY=2 # seconds
      - RESTART_TIMEOUT=1
      - RELOAD_CONTAINER=grafana
      - OBSERVER_TYPE=0 # standard = 0, polling = 1
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
      - ./grafana-dashboards/docker-dashboards:/docker-dashboards:ro

  restart_prometheus:
    image: apogiatzis/livereloading
    container_name: restart_prometheus
    privileged: true
    environment:
      - RELOAD_DELAY=2 # seconds
      - RESTART_TIMEOUT=1
      - RELOAD_CONTAINER=prometheus
      - OBSERVER_TYPE=0 # standard = 0, polling = 1
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
      - ./prometheus:/prometheus:ro
```

- To run this example, run the following

```Shell
cd test/monitoring
docker-compose -f docker-compose.yml -f docker-compose-reloaders.yml up -d
```

- To trigger this 2 step test
  1. Issue a save command (e.g. `Ctrl+s` on your editor of choice) on file [test/monitoring/grafana-dashboards/docker-dashboards/docker-and-system-monitoring.json](test/monitoring/grafana-dashboards/docker-dashboards/docker-and-system-monitoring.json)
  2. Issue a save command (e.g. `Ctrl+s` on your editor of choice) on file [test/monitoring/prometheus/prometheus.yml](test/monitoring/prometheus/prometheus.yml)
  3. Watch logs of both `reload_grafana_dashboards` & `restart_prometheus` containers using the command below

```Shell
docker-compose -f docker-compose.yml -f docker-compose-reloaders.yml logs -f reload_grafana_dashboards restart_prometheus

# Initial output
ttaching to reload_grafana_dashboards, restart_prometheus
reload_grafana_dashboards    | 21:47:08,215 reloader INFO Watching directory: /docker-dashboards
restart_prometheus           | 21:47:08,271 reloader INFO Watching directory: /prometheus

# Trigger output 1
reload_grafana_dashboards    | 21:48:14,809 reloader INFO <FileModifiedEvent: event_type=modified, src_path='/docker-dashboards/docker-and-system-monitoring.json', is_directory=False>
reload_grafana_dashboards    | 21:48:14,809 reloader INFO Scheduling reloading of containers
reload_grafana_dashboards    | 21:48:14,812 reloader INFO <FileModifiedEvent: event_type=modified, src_path='/docker-dashboards/docker-and-system-monitoring.json', is_directory=False>
reload_grafana_dashboards    | 21:48:14,812 reloader INFO Scheduling reloading of containers
reload_grafana_dashboards    | 21:48:14,819 reloader INFO <FileClosedEvent: event_type=closed, src_path='/docker-dashboards/docker-and-system-monitoring.json', is_directory=False>
reload_grafana_dashboards    | 21:48:14,819 reloader INFO Scheduling reloading of containers
reload_grafana_dashboards    | 21:48:16,819 reloader INFO Reloading container: grafana

# Trigger output 2
restart_prometheus           | 21:48:49,18 reloader INFO <FileModifiedEvent: event_type=modified, src_path='/prometheus/prometheus.yml', is_directory=False>
restart_prometheus           | 21:48:49,18 reloader INFO Scheduling reloading of containers
restart_prometheus           | 21:48:49,20 reloader INFO <FileModifiedEvent: event_type=modified, src_path='/prometheus/prometheus.yml', is_directory=False>
restart_prometheus           | 21:48:49,20 reloader INFO Scheduling reloading of containers
restart_prometheus           | 21:48:49,33 reloader INFO <FileClosedEvent: event_type=closed, src_path='/prometheus/prometheus.yml', is_directory=False>
restart_prometheus           | 21:48:49,33 reloader INFO Scheduling reloading of containers
restart_prometheus           | 21:48:51,33 reloader INFO Reloading container: prometheus
```

Observe that last lines in each reloader output logs, have correctly reloaded the exact targetted containers, more specific only `grafana` and not similarly named `grafana_barebones`

- To fully teardown the example run

```Shell
docker-compose -f docker-compose.yml -f docker-compose-reloaders.yml down -v
```

### Example - Single reloader, multiple folders - Multiple services

__Scenario:__ Simplify to a __single reloader__ that reloads both "production" `grafana` & `prometheus` on any change on watched folders:

- [test/monitoring/grafana/](test/monitoring/grafana/)
- [test/monitoring/prometheus/](test/monitoring/prometheus/)

Once again we use a common existing `RELOAD_LABEL` `single.reload` to target containers `grafana`, `prometheus` & mount all of the above folders on the single reloader, called `monitoring_watcher`

```yml
services:
  monitoring_watcher:
    image: apogiatzis/livereloading
    container_name: monitoring_watcher
    privileged: true
    environment:
      - RELOAD_DELAY=2 # seconds
      - RESTART_TIMEOUT=1
      - RELOAD_LABEL=single.reload
      - OBSERVER_TYPE=0 # standard = 0, polling = 1
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
      - ./grafana/:/grafana:ro
      - ./prometheus:/prometheus:ro
```

- To run this example, run the following

```Shell
cd test/monitoring
docker-compose -f docker-compose.yml -f docker-compose-single-reloader.yml up -d
```

- To trigger this simultaneous reload just issue a save command (e.g. `Ctrl+s` on your editor of choice) on any file under directories [test/monitoring/grafana/](test/monitoring/grafana/) or [test/monitoring/prometheus/](test/monitoring/prometheus/) and observe the logs.

```Shell
docker-compose -f docker-compose.yml -f docker-compose-single-reloader.yml logs -f monitoring_watcher

# Initial output
Attaching to monitoring_watcher
monitoring_watcher    | 21:59:49,366 reloader INFO Watching directory: /grafana
monitoring_watcher    | 21:59:49,366 reloader INFO Watching directory: /prometheus

# Trigger output
monitoring_watcher    | 22:00:24,428 reloader INFO <FileModifiedEvent: event_type=modified, src_path='/prometheus/prometheus.yml', is_directory=False>
monitoring_watcher    | 22:00:24,428 reloader INFO Scheduling reloading of containers
monitoring_watcher    | 22:00:24,433 reloader INFO <FileModifiedEvent: event_type=modified, src_path='/prometheus/prometheus.yml', is_directory=False>
monitoring_watcher    | 22:00:24,433 reloader INFO Scheduling reloading of containers
monitoring_watcher    | 22:00:24,438 reloader INFO <FileClosedEvent: event_type=closed, src_path='/prometheus/prometheus.yml', is_directory=False>
monitoring_watcher    | 22:00:24,438 reloader INFO Scheduling reloading of containers
monitoring_watcher    | 22:00:26,439 reloader INFO Reloading container: prometheus
monitoring_watcher    | 22:00:27,88 reloader INFO Reloading container: grafana
```

As you might observe on the log output, a single change on file [test/monitoring/prometheus/prometheus.yml](test/monitoring/prometheus/prometheus.yml) triggered a simultaneous reload of containers: `grafana` & `prometheus`. This way we can ensure that our monitoring stack reloads on configuration changes, on either side.

- To fully teardown the example run

```Shell
docker-compose -f docker-compose.yml -f docker-compose-single-reloader.yml down -v
```

### Summary

To sum-up this section, the possibilities of routing reloaders to services are up to your imagination. The following guidelines will help you achieve desired results:

- If you want to reload multiple containers, from a single reloader use a common existing `RELOAD_LABEL` and mount one or more needed volume mounts on reloader.
- If you want to route `n` reloaders to `n` containers 1-1, use multiple reloaders, each with a specific and unique `RELOAD_CONTAINER` value and the appropriate volume mount. Keep in mind that `RELOAD_CONTAINER` has to __exactly match__ the container name and is not matching all containers with a prefix e.g. `grafana` matches only that container name and not `grafana_barebones` in the previous example.
- What is not supported currently is the case of a single reloader with multiple volume mounts and a common existing `RELOAD_LABEL` reloading only the container, that has folder changes on its declared mount. It will reload all containers with the label, on __any change to any folder.__
- Reloader containers, can be named with any valid docker-compose name.

# Reloading Configration

The reloading can be configured from the environment variables of the `livereloader`
docker-compoe service. Here is a list of the available configuration variables:

- **RELOAD_CONTAINER**: The container name to target for reloading. (Required: False,
  but this or **RELOAD_LABEL** must be set if any containers are to be restarted)
- **RELOAD_LABEL**: A container label name.  All containers with that label name will be
  restarted. (Required: False, but this or **RELOAD_CONTAINER** must be set if any
  containers are to be restarted)
- **RELOAD_DELAY**: The number of seconds to wait before restarting the container
  (Required: False, Default: 1.5s)
- **RESTART_TIMEOUT**: The timeout period in seconds to wait for the container to
  restart. (Requied: False, Default: 10, same as the default timeout of Docker)
- **RELOAD_DIR**: The directory or directories to monitor for changes (multiple
  directories can be supplied, comma-separated). This can also be automatically derived
  from the mount directory in the livereloader service but in case you want to
  explicitly set it, this environment variable can be used.  (Required: False, Default:
  \<Mount Directory in Docker-compose\>)
- **OBSERVER_TYPE**: The type of observer to use. Supports two types: standard (0) and
  polling (1). Mounting your windows code directory into a linux container may cause
  the standard observer not to see changes made on the windows side ('inotify' is
  not triggered). The polling observer will trigger although at a slower pace.
  Another workaround suggests using the 'docker-windows-volume-watcher' package.
  (Required: False, Default: 0)
- **MUST_RUN**: If it should restart running containers only (1) yes (0) no
  (Required: False, Default: 1)

# Contribute

Feel free to open any issues and suggest improvements.
