#!/bin/bash
#
# (c) Samuel Cavallieri
# samuelcavallieri@gmail.com

source "${WL_HOME}/server/bin/setWLSEnv.sh"

WD=$(cd $(dirname $0); pwd)
source ${WD}/tools-env.sh || \
	{ echo "Variáveis de Ambiente Inválidas" ; exit 100; }


CLASSPATH="${CLASSPATH}:${WD}/jline-0.9.94.jar"
export CLASSPATH


cd ${DOMAIN_HOME}

${JAVA_HOME}/bin/java -Dprod.props.file=${WL_HOME}/.product.properties \
  jline.ConsoleRunner weblogic.WLST "$@"
