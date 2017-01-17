#!/bin/bash
#
# (c) Samuel Cavallieri
# samuelcavallieri@gmail.com

WD=$(cd $(dirname $0); pwd)
source ${WD}/tools-env.sh || \
	{ echo "Variáveis de Ambiente Inválidas" ; exit 100; }


CLASSPATH="${WL_HOME}/server/lib/weblogic.jar"
CLASSPATH="${CLASSPATH}:${WD}/jline-0.9.94.jar"
export CLASSPATH

if [[ $# > 0 && $1 != '-' ]]; then
	#Transforma caminho relativo em absoluto
	SCRIPT=$(readlink -mn $1)
	shift
fi


if [ -d ${DOMAIN_HOME} ]; then
	cd ${DOMAIN_HOME}
fi

${JAVA_HOME}/bin/java -Dpython.cachedir=${WD}/cachedir \
  -Dpython.path=${WL_HOME}/common/wlst/modules:${WD} \
  jline.ConsoleRunner org.python.util.jython $SCRIPT "$@"

