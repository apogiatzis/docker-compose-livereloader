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

## Example

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
```
docker-compose -f docker-compose.yml -f docker-compose-with-reloading.yml up
```

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


# Contribute

Feel free to open any issues and suggest improvements.