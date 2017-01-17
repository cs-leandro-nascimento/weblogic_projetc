#!/bin/bash
#
# (c) Samuel Cavallieri
# samuelcavallieri@gmail.com


source /ebusiness/install/install-env.sh


alias changedomain='unset DOMAIN_HOME; source /ebusiness/usr/tools/tools-env.sh'


unset DONT_SELECT_DOMAIN
if [ "$1" == "--dont-select-domain" ]; then
	DONT_SELECT_DOMAIN=True
fi


if [ ! -d "${INSTALL_ROOT}" ]; then
	shopt -q login_shell && return 101 \
		|| EXIT "INSTALL_ROOT=${INSTALL_ROOT} não é um diretório válido" 101
fi


if [ ! -d "${DOMAIN_ROOT}" ]; then
	shopt -q login_shell && return 102 \
		|| EXIT "DOMAIN_ROOT=${DOMAIN_ROOT} não é um diretório válido" 102
fi


if [ ! "${DONT_SELECT_DOMAIN}" -a ! "${DOMAIN_HOME}" ]; then

	unset DOMAIN_NAME
	declare -a DOMAINS=($(cd ${DOMAIN_ROOT}; ls))

	case ${#DOMAINS[@]} in
		0)
			;;

		1)
			DOMAIN_NAME=${DOMAINS[0]}
			;;

		*)
			WARN "Escolha o domínio:"
			select DOMAIN in ${DOMAINS[@]}; do
				if [ ${DOMAIN} ]; then
					DOMAIN_NAME=${DOMAIN}
					break
				fi
			done
		;;
	esac

	if [ "${DOMAIN_NAME}" ]; then
		DOMAIN_HOME=${DOMAIN_ROOT}/${DOMAIN_NAME}
		DOMAIN_APP=${APP_ROOT}/${DOMAIN_NAME}
	else
		unset DOMAIN_HOME
		unset DOMAIN_APP
	fi

	if [ -d "${DOMAIN_HOME}" ]; then
		ARR=($(
			. $DOMAIN_HOME/bin/setDomainEnv.sh;
			echo "${WL_HOME}";
			echo "${JAVA_HOME}";
		))

		WL_HOME=${ARR[0]}
		JAVA_HOME=${ARR[1]}
		PATH=$JAVA_HOME/bin:$PATH
	fi

	for var in INSTALL_ROOT APACHE_ROOT USR_ROOT DOMAIN_ROOT APP_ROOT \
			DOMAIN_HOME DOMAIN_APP WL_HOME JAVA_HOME PATH; do
		printf "${cyan}%-15s${normal} = %s\n" $var ${!var}
	done


fi

for var in DOMAIN_HOME DOMAIN_APP WL_HOME JAVA_HOME PATH; do
	export $var
done

