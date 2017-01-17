#!/usr/bin/env /ebusiness/usr/tools/jython.sh
#
# (c) Samuel Cavallieri
# samuelcavallieri@gmail.com
#

import sys
import os
import time

import wlstModule as wlst
import ConfigParser

from java.util import Properties
from java.lang import System
from java.io import FileInputStream
from java.io import FileOutputStream

from weblogic.security.internal import SerializedSystemIni
from weblogic.security.internal.encryption import ClearOrEncryptedService


config = None

class crtwls:
	def log(cls, message):
		print( "\n*** %s" % message)

	log = classmethod(log)


	def connectToAdminServer(cls):
		adminAddress = config.get('crtwls', 'admin-address')
		cls.log("Conectando ao AdminServer %s" % adminAddress)
		wlst.connect(url='t3://' + adminAddress)

	connectToAdminServer = classmethod(connectToAdminServer)


	def edit(cls, waitTime=0, timeout=0, start=True):
		cls.log("Indo para arvore de edicao")
		wlst.edit()

		if start:
			cls.log("Obtendo Lock da Console")
			wlst.startEdit(waitTime, timeout)

	edit = classmethod(edit)


	def save(cls):
		cls.log("Salvando a modificacao")
		wlst.save()

		cls.log("Ativando as mudancas")
		wlst.activate(block='true')

	save = classmethod(save)


	def getDomainName(cls):
		return wlst.cmo.getName()

	getDomainName = classmethod(getDomainName)


	def getAdminAddress(cls):
		adminAddress = config.get('crtwls', 'admin-address')
		return adminAddress

	getAdminAddress = classmethod(getAdminAddress)


	def getEnvSuffix(cls):
		envSuffix = config.get('crtwls', 'env-suffix')
		return envSuffix

	getEnvSuffix = classmethod(getEnvSuffix)






#==================================
def _wait(progress):
	crtwls.log("Aguardando a operacao %s" % progress.getCommandType())
	while progress.isRunning() == 1:
		progress.printStatus()
		print '##############################.',
		time.sleep(1)

	print '.'
	progress.printStatus()

	completed = progress.isCompleted() == 1
	crtwls.log("Operacao completada? %s" % completed)

	return completed


class Application:

	def __init__(self, name):
		if not name:
			raise ValueError("name required")

		name = name.strip()
		if len(name) == 0:
			raise ValueError("name required")

		self.name = name

		if not config.has_section(self.name):
			config.add_section(self.name)


	def group(self, group = None):

		if group:
			config.set(self.name, 'group', group)

		else:
			if config.has_option(self.name, 'group'):
				group = config.get(self.name, 'group')
			else:
				group = self.name

		return group


	def redeploy(self, path):

		crtwls.connectToAdminServer()

		reinstall = False
		remove = False

		applications = wlst.cmo.getAppDeployments()
		for application in applications:
			if application.getName() == self.name:
				reinstall = True
				break

#		if reinstall and application.getSourcePath() != path:
		if True:
			remove = True
			reinstall = False


		target = Cluster.resolveClusterName(self)

		try:
			if reinstall:
				crtwls.edit(10*60*1000, 5*60*1000)

				crtwls.log("Fazendo redeploy da Aplicacao '%s'" % self.name)
				progress = wlst.redeploy(self.name, block='true')
				wlst.activate()

			else:

				if remove:
					crtwls.edit(10*60*1000, 5*60*1000)

					crtwls.log("Fazendo undeploy da Aplicacao '%s'" % self.name)
					progress = wlst.undeploy(self.name, block='true')
					wlst.activate()

				crtwls.edit(10*60*1000, 5*60*1000)

				crtwls.log("Fazendo deploy da Aplicacao '%s'" % self.name)
				progress = wlst.deploy(self.name, path, target, block='true')
				wlst.activate()
		except wlst.WLSTException, e:
				e.printStackTrace()
				raise e


	def __findSid__(self, url):
		idx = url.find('SERVICE_NAME')
		if idx < 0:
			idx = url.find('SID')

		if not idx < 0:
			sta = url.find('=', idx) + 1
			end = url.find(')', sta)
			return url[sta:end].strip()

		idx = url.find('@')
		sta = url.rfind('/', idx)
		if sta < 0:
			sta = url.rfind(':', idx)

		sta = sta + 1
		return url[sta:].strip()


	def newDatasource(self, name, url, username, password, isXA):
		# Reduz espaços repetidos
		url = ' '.join(url.split())

		sid = self.__findSid__(url)
		dsName = "%s / %s" % (username, sid)
		dsName = dsName.lower()

		if isXA:
			dsName = dsName + ' - XA'

		#config.set(self.name, 'ds.'+name+'.url', url)
		#config.set(self.name, 'ds.'+name+'.username', username)
		#config.set(self.name, 'ds.'+name+'.password', password)

		crtwls.connectToAdminServer()
		crtwls.edit()

		cluster = Cluster.findCluster(self)

		if not cluster:
			raise Exception("Cluster da aplicacao %s nao encontrado" % self.name)

		crtwls.log("Criando o DataSource")
		datasource = wlst.cmo.createJDBCSystemResource(dsName)

		jdbcResource = datasource.getJDBCResource()
		jdbcResource.setName(dsName)

		jndiName = '%s.ds.%s' % (self.name, name)
		jdbcResource.getJDBCDataSourceParams().setJNDINames([jndiName])

		jdbcResource.getJDBCConnectionPoolParams().setInitialCapacity(0)
		jdbcResource.getJDBCConnectionPoolParams().setMaxCapacity(20)
		jdbcResource.getJDBCConnectionPoolParams().setShrinkFrequencySeconds(900)
		jdbcResource.getJDBCConnectionPoolParams().setTestConnectionsOnReserve(True)
		jdbcResource.getJDBCConnectionPoolParams().setStatementCacheSize(30)
		jdbcResource.getJDBCConnectionPoolParams().setStatementCacheType('LRU')

		if isXA:
			jdbcResource.getJDBCDriverParams().setDriverName('oracle.jdbc.xa.client.OracleXADataSource')
		else:
			jdbcResource.getJDBCDriverParams().setDriverName('oracle.jdbc.OracleDriver')
		jdbcResource.getJDBCDriverParams().setPassword(password)
		jdbcResource.getJDBCDriverParams().setUrl(url)

		props = jdbcResource.getJDBCDriverParams().getProperties()
		props.createProperty('user')
		props.lookupProperty('user').setValue(username)

		crtwls.log("Ajustando Target")
		datasource.addTarget(cluster)

		crtwls.save()


	def newMultiDatasource(self, name, dsList):
		dsName = "%s.ds.%s" % (self.name, name)
		dsName = dsName.lower()

		crtwls.connectToAdminServer()
		crtwls.edit()

		cluster = Cluster.findCluster(self)

		if not cluster:
			raise Exception("Cluster da aplicacao %s nao encontrado" % self.name)

		crtwls.log("Criando o MultiDataSource")
		datasource = wlst.cmo.createJDBCSystemResource(dsName)

		jdbcResource = datasource.getJDBCResource()
		jdbcResource.setName(dsName)

		jndiName = '%s.ds.%s' % (self.name, name)
		jdbcResource.getJDBCDataSourceParams().setJNDINames([jndiName])
		jdbcResource.getJDBCDataSourceParams().setAlgorithmType('Load-Balancing')
		jdbcResource.getJDBCDataSourceParams().setDataSourceList(dsList)

		crtwls.log("Ajustando Target")
		datasource.addTarget(cluster)

		crtwls.save()


	def createEnv(self, group = None):
		crtwls.connectToAdminServer()

		domainApp = System.getenv("DOMAIN_APP")
		usrRoot = System.getenv("USR_ROOT")

		if os.path.exists('%s/install/%s' % (domainApp, self.name)):
			raise Exception("Ambiente de %s já existe" % self.name)


		self.group(group)

		site = self.name
		cfgvars = {'APP_NAME' : self.name, 'SITE' : site,
			'ENV' : crtwls.getEnvSuffix(), 'DOMAIN_APP' : domainApp,
			'DOMAIN_NAME' : crtwls.getDomainName(),
			'CLUSTER' : '${WLS_CLUSTER_%s}' % self.group()}


		crtwls.log("Criando diretórios")
		DIRS = ['appfiles', 'applogs', 'config', 'deployments',
			'docroot', 'install']

		for d in DIRS:
			os.makedirs('%s/%s/%s' % (domainApp, d, self.name))


		crtwls.log("Criando arquivo config.properties")
		template = open('%s/tools/config-properties.tmpl' % usrRoot, 'r').read()

		cfgname = '%s/config/%s/config.properties' % (domainApp, self.name)
		cfgfile = open(cfgname, 'w')
		cfgfile.write(template % cfgvars)
		cfgfile.close()


		cfgname = '%s/httpconf/%s.cfg' % (domainApp, site)

		if not os.path.exists(cfgname):
			crtwls.log("Criando Apache VirtualHost '%s'" % site)
			template = open('%s/tools/virtualhost.tmpl' % usrRoot, 'r').read()

			cfgfile = open(cfgname, 'w')
			cfgfile.write(template % cfgvars)
			cfgfile.close()

			os.makedirs('%s/httplogs/%s' % (domainApp, site))
		else:
			crtwls.log("Apache VirtualHost '%s' já existe" % site)







class JMSModule:

	def resolveJMSModuleName(cls, application):
		group = application.group()
		jmsModuleName = '%s-jms' % group
		return jmsModuleName

	resolveJMSModuleName = classmethod(resolveJMSModuleName)


	def findJMSModule(cls, application):
		jmsName = cls.resolveJMSModuleName(application)
		crtwls.log("Buscando o JMS Module %s" % jmsName)
		jmsModule = wlst.cmo.lookupJMSSystemResource(jmsName)
		return jmsModule

	findJMSModule = classmethod(findJMSModule)


	def ensureJMSServers(cls, cluster):

		servers = cluster.getServers()

		for server in servers:
			serverName = server.getName()
			jmsServerName = serverName + '-jms'

			jmsserver = wlst.cmo.lookupJMSServer(jmsServerName)

			if not jmsserver:
				crtwls.log("Criando o JMSServer '%s'" % jmsServerName)
				jmsserver = wlst.cmo.createJMSServer(jmsServerName)
				jmsserver.addTarget(server)

				crtwls.log("Configurando o JMSServer Log")
				jmsserver.getJMSMessageLogFile().setFileName('logs/%s-jms.log' % serverName)
				jmsserver.getJMSMessageLogFile().setFileMinSize(40000)
				jmsserver.getJMSMessageLogFile().setNumberOfFilesLimited(True)
				jmsserver.getJMSMessageLogFile().setFileCount(5)

	ensureJMSServers = classmethod(ensureJMSServers)


	def __createJMSModule(cls, application, cluster):
		jmsName = cls.resolveJMSModuleName(application)

		crtwls.log("Criando o JmsModule")
		cls.ensureJMSServers(cluster)
		jmsmodule = wlst.cmo.createJMSSystemResource(jmsName)

		crtwls.log("Ajustando Targets")
		jmsmodule.addTarget(cluster)

		crtwls.log("Criando Default Connection Factory")
		connection = jmsmodule.getJMSResource().createConnectionFactory('jms.ConnectionFactory.default')
		connection.setJNDIName('jms.ConnectionFactory.default')
		connection.setDefaultTargetingEnabled(True)

		return jmsmodule

	__createJMSModule = classmethod(__createJMSModule)


	def createJMSQueue(cls, application, name):
		crtwls.connectToAdminServer()

		cluster = Cluster.findCluster(application)

		if not cluster:
			raise Exception("Cluster da aplicacao %s nao encontrado" % application.name)

		crtwls.edit()

		jmsmodule = cls.findJMSModule(application)

		if not jmsmodule:
			jmsmodule = cls.__createJMSModule(application, cluster)
#			raise Exception("JMS Module da aplicacao %s nao encontrado" % application.name)

		crtwls.log("Criando o JmsQueue")
		jmsQueueName = '%s.jms.%s' % (application.name, name)
		jmsQueue = jmsmodule.getJMSResource().createUniformDistributedQueue(jmsQueueName)
		jmsQueue.setJNDIName(jmsQueueName)
		jmsQueue.setDefaultTargetingEnabled(True)

		crtwls.save()

	createJMSQueue = classmethod(createJMSQueue)










class Cluster:

	def createCluster(cls, application):
		clusterName = cls.resolveClusterName(application)

		crtwls.connectToAdminServer()
		crtwls.edit()

		crtwls.log("Criando o Cluster")
		cluster = wlst.cmo.createCluster(clusterName)

		crtwls.log("Configurando o Cluster %s" % clusterName)
		cluster.setWeblogicPluginEnabled(True)
		cluster.setClusterMessagingMode('unicast')

		crtwls.log("Ajustando Targets dos MailSession")
		mailsessions = wlst.cmo.getMailSessions()
		for mailsession in mailsessions:
			mailsession.addTarget(cluster)
			crtwls.log(".. %s" % mailsession.getName())

		crtwls.save()

	createCluster = classmethod(createCluster)


	def resolveClusterName(cls, application):
		mask = '%s-cluster'

		if config.has_option('crtwls', 'cluster-name-mask'):
			mask = config.get('crtwls', 'cluster-name-mask')

		group = application.group()
		clusterName = mask % group
		return clusterName

	resolveClusterName = classmethod(resolveClusterName)


	def findCluster(cls, application):
		clusterName = cls.resolveClusterName(application)
		crtwls.log("Buscando o Cluster %s" % clusterName)
		cluster = wlst.cmo.lookupCluster(clusterName)
		return cluster

	findCluster = classmethod(findCluster)


	__JROCKIT = '-jrockit -Xms%s -Xmx%s -Xgc:genpar \
-Xmanagement:ssl=false,port=%d -Dweblogic.wsee.useRequestHost=true \
-Djava.awt.headless=true -Dconfig.applogssuffix=${weblogic.Name} \
-Dconfig.applogspath=%s/applogs'

	__HOTSPOT = '-server -Xms%s -Xmx%s -XX:MaxPermSize=256M \
-Dcom.sun.management.jmxremote.port=%d -Dcom.sun.management.jmxremote.ssl=false \
-Djavax.management.builder.initial=weblogic.management.jmx.mbeanserver.WLSMBeanServerBuilder \
-Dweblogic.wsee.useRequestHost=true \
-Djava.awt.headless=true -Dconfig.applogssuffix=${weblogic.Name} \
-Dconfig.applogspath=%s/applogs'

	def createManagedServer(cls, application, hostname, port, serial, memory='1G'):
		vendor = System.getenv("JAVA_VENDOR")
		CMDLINE = vendor == 'SUN' and cls.__HOTSPOT or cls.__JROCKIT

		if not memory:
			memory = '1G'

		crtwls.connectToAdminServer()
		crtwls.edit()

		cluster = cls.findCluster(application)
		if not cluster:
			raise Exception("Cluster da aplicacao %s nao encontrado" % application.name)

		mcn = Domain.findMachine(hostname)
		if not mcn:
			raise Exception("Machine do hostname %s nao encontrado" % hostname)


		domainName = crtwls.getDomainName()
		shortname = hostname.split('.')[0]
		group = application.group()

		serverName = '%s-%s-%s-%s' % (domainName, group, shortname, serial)

		crtwls.log("Buscando o Server")
		server = wlst.cmo.lookupServer(serverName)

		if not server:
			crtwls.log("Criando o Server")
			server = wlst.cmo.createServer(serverName)

		server.setCluster(cluster)
		server.setMachine(mcn)


		crtwls.log("Configurando o Server '%s'" % serverName)
		server.setListenAddress(hostname)
		server.setListenPort(port)
		server.setWeblogicPluginEnabled(True)

		server.getSSL().setEnabled(True)
		server.getSSL().setListenPort(int(port) + 1)

		crtwls.log("Ajustando Deployment Options")
		server.setUploadDirectoryName('/nonexistent')
		server.setStagingMode('nostage')


		crtwls.log("Ajustando Server StartUp Options")
		domainApp = System.getenv("DOMAIN_APP")
		cmdLine = CMDLINE % (memory, memory, port +2, domainApp)
		server.getServerStart().setArguments(cmdLine)


		crtwls.log("Configurando o Server Log")
		server.getLog().setFileName('logs/%s-server.log' % serverName)
		server.getLog().setFileMinSize(40000)
		server.getLog().setNumberOfFilesLimited(True)
		server.getLog().setFileCount(5)

		crtwls.log("Configurando o WebServer")
		server.getWebServer().setMaxPostSize(23068672)

		crtwls.log("Configurando o WebServer Log")
		server.getWebServer().getWebServerLog().setFileName('logs/%s-access.log' % serverName)
		server.getWebServer().getWebServerLog().setFileMinSize(40000)
		server.getWebServer().getWebServerLog().setNumberOfFilesLimited(True)
		server.getWebServer().getWebServerLog().setFileCount(5)

		crtwls.log("Criando link simbolico em serverlogs")
                relativeLogPath = "../../../domains/" + domainName + "/servers/" + serverName + "/logs"
                linkName = domainApp + "/serverlogs/" + serverName
		os.system('ln -s ' + relativeLogPath + ' ' + linkName)

		jmsModule = JMSModule.findJMSModule(application)
		if jmsModule:
			JMSModule.ensureJMSServers(cluster)

		crtwls.save()

	createManagedServer = classmethod(createManagedServer)









class Domain:


	def create(cls, domainName, envSuffix, adminAddress):
		wlHome = System.getenv('WL_HOME')
		usrRoot = System.getenv("USR_ROOT")
		appRoot = System.getenv('APP_ROOT')
		domainRoot = System.getenv('DOMAIN_ROOT')
		apacheRoot = System.getenv('APACHE_ROOT')

		hostname, port = adminAddress.split(':')
		port = int(port)
		adminName = '%s-adminserver' % domainName

		domainHome = '%s/%s' % (domainRoot, domainName)
		domainApp = "%s/%s" % (appRoot, domainName)

		cfgvars = {'DOMAIN_NAME' : domainName,
			'CLUSTER' : adminAddress, 'ENV' : envSuffix}

		wlst.readTemplate('%s/../basedomain.jar' % wlHome)
		wlst.cmo.setName(domainName);

		wlst.cmo.getServers()[0].setName(adminName)
		wlst.cmo.getServers()[0].setListenAddress(hostname)
		wlst.cmo.getServers()[0].setListenPort(port)
		wlst.cmo.setAdminServerName(adminName)

		wlst.writeDomain(domainHome)


		crtwls.log("Criando diretórios")
		os.makedirs('%s/jmsstores' % (domainHome))

		DIRS = ['appfiles', 'applogs', 'config', 'deployments',
			'docroot', 'install', 'httplogs', 'httpconf', 'serverlogs']

		for d in DIRS:
			os.makedirs('%s/%s' % (domainApp, d))


		crtwls.log("Criando common.properties")
		cfgname = '%s/config/common.properties' % (domainApp)
		cfgfile = open(cfgname, 'w')
		cfgfile.write('allowjobfrom=\n')
		cfgfile.close()


		crtwls.log("Criando Apache VirtualHost")
		template = open('%s/tools/domainhost.tmpl' % usrRoot, 'r').read()

		cfgname = '%s/httpconf/default.conf' % (domainApp)
		cfgfile = open(cfgname, 'w')
		cfgfile.write(template % cfgvars)
		cfgfile.close()

		open('%s/httpconf/manutencao.txt' % (domainApp), 'w').close()
		os.makedirs('%s/httplogs/default' % (domainApp))


		crtwls.log("Incluindo o VirtualHost no Apache Conf")
		template = 'Include ${APP_ROOT}/%(DOMAIN_NAME)s/httpconf/default.conf\n'

		cfgname = '%s/conf.d/%s.cfg' % (apacheRoot, domainName)
		cfgfile = open(cfgname, 'w')
		cfgfile.write(template % cfgvars)
		cfgfile.close()


		crtwls.log("Criando crtwls.cfg")
		template = '[crtwls]\nadmin-address = %(CLUSTER)s\nenv-suffix = %(ENV)s\n'

		cfgname = '%s/crtwls.cfg' % (domainHome)
		cfgfile = open(cfgname, 'w')
		cfgfile.write(template % cfgvars)
		cfgfile.close()


		crtwls.log("Criando startEnv.sh")
		template = 'ADMIN_NAME=%s\nNM_PORT=%d\n'

		cfgname = '%s/startEnv.sh' % (domainHome)
		cfgfile = open(cfgname, 'w')
		cfgfile.write(template % (adminName, port + 4))
		cfgfile.close()


		crtwls.log("Copiando boot.properties")
		template = open('%s/servers/%s/security/boot.properties'
						% (domainHome, adminName), 'r').read()

		cfgname = '%s/boot.properties' % (domainHome)
		cfgfile = open(cfgname, 'w')
		cfgfile.write(template)
		cfgfile.close()


	create = classmethod(create)




	def authenticator(cls):
		crtwls.connectToAdminServer()
		crtwls.edit()

		crtwls.log("Identificando o REALM")
		realm = wlst.cmo.getSecurityConfiguration().getDefaultRealm()

		crtwls.log("Buscando o autenticador 'Petrobras AD Authenticator'")
		auth = realm.lookupAuthenticationProvider('Petrobras AD Authenticator')

		if not auth:
			crtwls.log("Criando o autenticador 'Petrobras AD Authenticator'")
			auth = realm.createAuthenticationProvider('Petrobras AD Authenticator',
				'weblogic.security.providers.authentication.ActiveDirectoryAuthenticator')

		crtwls.log("Configurando o autenticador 'Petrobras AD Authenticator'")
		auth.setGroupBaseDN('DC=biz')
		auth.setUserNameAttribute('sAMAccountName')
		auth.setConnectionRetryLimit(3)
		auth.setConnectTimeout(10)
		auth.setParallelConnectDelay(5)
		auth.setResultsTimeLimit(1000)
		auth.setAllUsersFilter('objectClass=user')
		auth.setPropagateCauseForLoginException(False)
		auth.setHost('sptbrdc04.petrobras.biz sptbrdc14.petrobras.biz sptbrdc08.petrobras.biz sptbrdc02.petrobras.biz')
		auth.setAllGroupsFilter('objectClass=group')
		auth.setUseTokenGroupsForGroupMembershipLookup(True)
		auth.setUserFromNameFilter('(&(samAccountName=%u)(objectclass=user))')
		auth.setGroupFromNameFilter('(&(sAMAccountName=%g)(objectclass=group))')
		auth.setPort(3268)
		auth.setUserBaseDN('DC=biz')
		auth.setStaticGroupNameAttribute('sAMAccountName')
		auth.setPrincipal('sacduxba@petrobras.biz')
		auth.setCredential('--------')
		auth.setControlFlag('SUFFICIENT')
		auth.setEnableSIDtoGroupLookupCaching(True)


		crtwls.log("Configurando outros autenticadores")

		from weblogic.management.security.authentication import AuthenticatorMBean
		for tmp in realm.getAuthenticationProviders():
			if isinstance(tmp, AuthenticatorMBean):
				crtwls.log(".. Ajustando ControlFlag de '%s' para SUFFICIENT" % tmp.getName())
				tmp.setControlFlag('SUFFICIENT')

		crtwls.save()

		crtwls.log("Configurando grupo Administrador")
		wlst.serverConfig()
		realm = wlst.cmo.getSecurityConfiguration().getDefaultRealm()

		mapper = realm.lookupRoleMapper('XACMLRoleMapper')

		expr = '{Grp(Administrators)|Grp(GG_BA_TICBA_UNIX_WEB_ADMINS)}'
		mapper.setRoleExpression(None, 'Admin', expr)

		expr = '{Grp(AppTesters)|Usr(sawjciba)}'
		mapper.setRoleExpression(None, 'AppTester', expr)

	authenticator = classmethod(authenticator)


	def configure(cls):
		crtwls.connectToAdminServer()
		crtwls.edit()

		domainName = wlst.cmo.getName()

		crtwls.log("Configurando o Domain Log")
		wlst.cmo.getLog().setFileMinSize(40000)
		wlst.cmo.getLog().setNumberOfFilesLimited(True)
		wlst.cmo.getLog().setFileCount(5)

		crtwls.log("AdminServer - Configurando")
		server = wlst.cmo.lookupServer(domainName + '-adminserver')

		crtwls.log("AdminServer - Ajustando WeblogicPluginEnabled")
		server.setWeblogicPluginEnabled(True)

		crtwls.log("AdminServer - Ajustando UploadDirectoryName")
		server.setUploadDirectoryName('/nonexistent')

		crtwls.log("AdminServer - Configurando o Server Log")
		server.getLog().setFileMinSize(40000)
		server.getLog().setNumberOfFilesLimited(True)
		server.getLog().setFileCount(5)

		crtwls.log("AdminServer - Configurando o WebServer")
		server.getWebServer().setMaxPostSize(15728640)
		server.getWebServer().setFrontendHost('%s.petrobras.com.br' % domainName)
		server.getWebServer().setFrontendHTTPPort(80)

		crtwls.log("AdminServer - Configurando o WebServer Log")
		server.getWebServer().getWebServerLog().setFileMinSize(40000)
		server.getWebServer().getWebServerLog().setNumberOfFilesLimited(True)
		server.getWebServer().getWebServerLog().setFileCount(5)

		crtwls.save()

	configure = classmethod(configure)


	def listDatasource(cls):
		crtwls.connectToAdminServer()
		crtwls.edit(False)

		datasources = wlst.cmo.getJDBCSystemResources()

		for datasource in datasources:
			jdbcResource = datasource.getJDBCResource()

			jndiName = jdbcResource.getJDBCDataSourceParams().getJNDINames()[0]
			jndiName = jndiName.split('.')
			appName = jndiName[0]
			name = jndiName[2]

			dsList = jdbcResource.getJDBCDataSourceParams().getDataSourceList()

			if dsList:
				print '%s new-multidatasource %s "%s"' % (appName, name, dsList)

			else:
				drivername = jdbcResource.getJDBCDriverParams().getDriverName()
				password = jdbcResource.getJDBCDriverParams().getPassword()
				url = jdbcResource.getJDBCDriverParams().getUrl()

				props = jdbcResource.getJDBCDriverParams().getProperties()
				username = props.lookupProperty('user').getValue()

				if drivername == 'oracle.jdbc.xa.client.OracleXADataSource':
					cmd = 'new-xadatasource'
				else:
					cmd = 'new-datasource'

				print '%s %s %s "%s" %s %s' % (appName, cmd, name, url, username, password)



	listDatasource = classmethod(listDatasource)


	def findMachine(cls, hostname):
		machines = wlst.cmo.getMachines()
		for machine in machines:
			if machine.getNodeManager().getListenAddress() == hostname:
				return machine

	findMachine = classmethod(findMachine)


	def createMachine(cls, hostname):
		adminAddress = crtwls.getAdminAddress()

		port = int(adminAddress.split(':')[1]) + 4;
		name = hostname.split('.')[0]

		crtwls.connectToAdminServer()
		crtwls.edit()

		crtwls.log("Criando a Machine")
		nmgr = wlst.cmo.createMachine(name)

		crtwls.log("Configurando a Machine %s" % name)
		nmgr.getNodeManager().setListenAddress(hostname)
		nmgr.getNodeManager().setListenPort(port)
		nmgr.getNodeManager().setDebugEnabled(True)

		crtwls.save()

	createMachine = classmethod(createMachine)


	def mailSession(cls):
		crtwls.connectToAdminServer()
		crtwls.edit()

		crtwls.log("Buscando o MailSession")
		mailsession = wlst.cmo.lookupMailSession('mail.default')

		if not mailsession:
			crtwls.log("Criando o MailSession")
			mailsession = wlst.cmo.createMailSession('mail.default')

		mailsession.setJNDIName('mail.default')

		crtwls.log("Ajustando Targets")
		clusters = wlst.cmo.getClusters()
		for cluster in clusters:
			mailsession.addTarget(cluster)
			crtwls.log(".. %s" % cluster.getName())

		crtwls.log("Ajustando as configurações de SMTP")
		props = Properties()
		props.setProperty('mail.transport.protocol', 'smtp')
		props.setProperty('mail.smtp.host', 'smtp.petrobras.com.br')
		props.setProperty('mail.smtp.port', '25')
		props.setProperty('mail.smtp.connectiontimeout', '5000')
		props.setProperty('mail.smtp.timeout', '10000')
		mailsession.setProperties(props)

		crtwls.save()

	mailSession = classmethod(mailSession)


	def undeployApps():
		crtwls.connectToAdminServer()

		crtwls.log("Obtendo lista de Aplicacoes")
		appList = wlst.cmo.getAppDeployments()

		for app in appList:
			if not app.getName().startswith('crtwls-'):
				crtwls.log("Desinstalando Aplicacao: " + app.getName())
				wlst.undeploy(app.getName())

	undeployApps = classmethod(undeployApps)


	def decrypt(cls, encryptedText):
		domainHome = System.getenv("DOMAIN_HOME")
		encryptionService = SerializedSystemIni.getEncryptionService(domainHome)
		ceService = ClearOrEncryptedService(encryptionService)

		clearText = ceService.decrypt(encryptedText)
		print '>>', clearText

	decrypt = classmethod(decrypt)


	def decryptProperties(cls, propertiesFile):
		domainApp = System.getenv("DOMAIN_APP")
		domainHome = System.getenv("DOMAIN_HOME")

		encryptionService = SerializedSystemIni.getEncryptionService(domainHome)
		ceService = ClearOrEncryptedService(encryptionService)

		propertiesFile = '%s/%s' % (domainApp, propertiesFile)
		fis = FileInputStream(propertiesFile)
		props = Properties()
		props.load(fis)
		fis.close()

		changed = False

		for entry in props.entrySet():
			value = entry.getValue()

			if ceService.isEncrypted(value):
				clearText = ceService.decrypt(value)
				props.setProperty(entry.getKey(), clearText);
				changed = True

		if changed:
			fos = FileOutputStream(propertiesFile)
			props.store(fos, None)
			fos.close()

	decryptProperties = classmethod(decryptProperties)


	def restartRunningManagedServers(cls):
		crtwls.connectToAdminServer()
		wlst.domainRuntime()
		server_lifecycles = wlst.cmo.getServerLifeCycleRuntimes()

		for server_lifecycle in server_lifecycles:
			if (server_lifecycle.getState() == 'RUNNING' and server_lifecycle.getName() != wlst.serverName):
				wlst.shutdown(server_lifecycle.getName(),'Server','true',1000, block='true')
				print "Waiting process to shutdown..."
				while (server_lifecycle.getState() != "SHUTDOWN"):
					time.sleep(1)
					print "."
				print "OK"
				wlst.start(server_lifecycle.getName())
			else:
				print 'Doing nothing: ' + server_lifecycle.getName() + ' state: ' + server_lifecycle.getState()

	restartRunningManagedServers = classmethod(restartRunningManagedServers)




def usage():
	print "Usage: %s" % sys.argv[0]

	print """
	domain create <domainName> <envSuffix> <adminAddress>
	domain configure
	domain configure-authenticator
	domain configure-mailsession
	domain create-machine <hostname>
	domain list-datasource
	domain undeploy-apps
	domain decrypt <text>
	domain decrypt-properties <file> #inline decrypt
	domain restart-running-servers
	application <appname> create-env [group]
	application <appname> create-cluster
	application <appname> create-server <hostname> <port> <serial> [memory]
	application <appname> new-datasource <name> <url> <username> <password>
	application <appname> new-xadatasource <name> <url> <username> <password>
	application <appname> new-multidatasource <name> <dslist>
	application <appname> new-jmsqueue <name>
	application <appname> redeploy <path>
	"""
	sys.exit(2)


def openConfig():
	global config

	config = ConfigParser.ConfigParser()

	try:
		cfgfile = open('crtwls.cfg')
		config.readfp(cfgfile)
	except IOError, e:
		pass

def closeConfig():
	global config

	cfgfile = open('crtwls.cfg', 'wb')
	config.write(cfgfile)


def argv(idx):
	if len(sys.argv) <= idx:
		usage()

	return sys.argv[idx]


if __name__ == "__main__":
	try:
		openConfig()

		cmd = argv(1)

		if cmd == 'application':
			appName = argv(2)
			subcmd = argv(3)

			application = Application(appName)

			if subcmd == 'create-env':
				group = None
				if len(sys.argv) > 4:
					group = argv(4)

				application.createEnv(group)

			elif subcmd == 'create-cluster':
				Cluster.createCluster(application)

			elif subcmd == 'create-server':
				hostname = argv(4)
				port = int(argv(5))
				serial = argv(6)

				memory = None
				if len(sys.argv) > 7:
					memory = argv(7)

				Cluster.createManagedServer(application, hostname, port, serial, memory)

			elif subcmd == 'new-datasource':
				name = argv(4)
				url = argv(5)
				username = argv(6)
				password = argv(7)
				application.newDatasource(name, url, username, password, False)

			elif subcmd == 'new-xadatasource':
				name = argv(4)
				url = argv(5)
				username = argv(6)
				password = argv(7)
				application.newDatasource(name, url, username, password, True)

			elif subcmd == 'new-multidatasource':
				name = argv(4)
				dsList = argv(5)
				application.newMultiDatasource(name, dsList)

			elif subcmd == 'new-jmsqueue':
				name = argv(4)
				JMSModule.createJMSQueue(application, name)

			elif subcmd == 'redeploy':
				path = argv(4)
				application.redeploy(path)




		elif cmd == 'domain':
			subcmd = argv(2)

			if subcmd == 'create':
				domainName = argv(3)
				envSuffix = argv(4)
				adminAddress = argv(5)
				Domain.create(domainName, envSuffix, adminAddress)

			elif subcmd == 'configure':
				Domain.configure()

			elif subcmd == 'configure-authenticator':
				Domain.authenticator()

			elif subcmd == 'list-datasource':
				Domain.listDatasource()

			elif subcmd == 'configure-mailsession':
				Domain.mailSession()

			elif subcmd == 'create-machine':
				hostname = argv(3)
				Domain.createMachine(hostname)

			elif subcmd == 'undeploy-apps':
				Domain.undeployApps()

			elif subcmd == 'decrypt':
				text = argv(3)
				Domain.decrypt(text)

			elif subcmd == 'decrypt-properties':
				propertiesFile = argv(3)
				Domain.decryptProperties(propertiesFile)

			elif subcmd == 'restart-running-servers':
				Domain.restartRunningManagedServers()

		else:
			usage()

	finally:
		closeConfig()



