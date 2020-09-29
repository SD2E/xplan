# Allow over-ride
if [ -z "${CONTAINER_IMAGE}" ]
then
    version=$(cat ./_util/VERSION)
    CONTAINER_IMAGE="index.docker.io/library/ubuntu:bionic"
fi
. lib/container_exec.sh

# Write an excution command below that will run a script or binary inside the 
# requested container, assuming that the current working directory is 
# mounted in the container as its WORKDIR. In place of 'docker run' 
# use 'container_exec' which will handle setup of the container on 
# a variety of host environments. 
#
# Here is a template:
#
# container_exec ${CONTAINER_IMAGE} COMMAND OPTS INPUTS
#
# Here is an example of counting words in local file 'poems.txt',
# outputting to a file 'wc_out.txt'
#
# container_exec ${CONTAINER_IMAGE} wc poems.txt > wc_out.txt
#

# set -x

# set +x
COMMAND="python3"
if [ -z "${lab_configuration}" ]
then
    echo "Running xplan design app with lab_configuration dictionary as input"
    PARAMS="/run.py ${experiment_id} ${challenge_problem} ${out_path} ${experiment_dir} ${state_json} --lab_configuration_uri ${lab_configuration_uri}"
else
    echo "Running xplan design app with lab_configuration uri as input"
    PARAMS="/run.py ${experiment_id} ${challenge_problem} ${out_path} ${experiment_dir} ${state_json} --lab_configuration ${lab_configuration}"
fi

if [ -n "${xplan_test}" ]
then
    echo "Running with test flag"
    PARAMS="${PARAMS} --test"
fi

# echo container_exec ${CONTAINER_IMAGE} ${COMMAND} ${PARAMS}
container_exec ${CONTAINER_IMAGE} ${COMMAND} ${PARAMS}