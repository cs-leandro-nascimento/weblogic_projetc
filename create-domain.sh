#!/bin/bash
#
# (c) Samuel Cavallieri
# samuelcavallieri@gmail.com

if [ $# != 4 ]; then
	echo "usage: $0 domain_name env_suffix admin_address:port wl_home"
	exit 1;
fi


WD=$(cd $(dirname $0); pwd)
source ${WD}/tools-env.sh --dont-select-domain || \
	{ echo "Variáveis de Ambiente Inválidas" ; exit 100; }


TRACE "Criando o domínio"


ENV_SUFFIX="$2"
DOMAIN_NAME=$(echo $1${ENV_SUFFIX} | tr 'A-Z' 'a-z')
DOMAIN_HOME=${DOMAIN_ROOT}/${DOMAIN_NAME}

ADMIN_ADDRESS="$3"
WL_HOME="$4"

INFO "Resolvendo JAVA_HOME"
JAVA_HOME=$( CMD ". ${WL_HOME}/common/bin/commEnv.sh ; echo \$JAVA_HOME" 201 )


TRACE "Criando o domínio"
CMD "${USR_ROOT}/tools/sgwl.py domain create ${DOMAIN_NAME} ${ENV_SUFFIX} ${ADMIN_ADDRESS}" 202


TRACE "Copiando \${WL_HOME}/server/bin/startNodeManager.sh para \${DOMAIN_HOME}/bin"
CMD "cp -vf ${WL_HOME}/server/bin/startNodeManager.sh ${DOMAIN_HOME}/bin" 220
CMD "sed -i -e 's|\(NODEMGR_HOME="${WL_HOME}/common/nodemanager"\)|#\\\\1|' \\
    ${DOMAIN_HOME}/bin/startNodeManager.sh" 221


TRACE "Copiando \${INSTALL_ROOT}/start.sh para \${DOMAIN_HOME}"
CMD "cp -vf ${INSTALL_ROOT}/start.sh ${DOMAIN_HOME}" 222
CMD "chmod u+x ${DOMAIN_HOME}/start.sh" 223


TRACE "Copiando \${INSTALL_ROOT}/startNM.sh para \${DOMAIN_HOME}"
CMD "cp -vf ${INSTALL_ROOT}/startNM.sh ${DOMAIN_HOME}" 224
CMD "chmod u+x ${DOMAIN_HOME}/startNM.sh" 225



