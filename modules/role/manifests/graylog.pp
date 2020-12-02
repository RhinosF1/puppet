# role: graylog
class role::graylog {
    include ssl::wildcard
    include ::java

    nginx::site { 'graylog_proxy':
        ensure  => present,
        source  => 'puppet:///modules/role/graylog/graylog.miraheze.org.conf',
    }

    class { 'mongodb::globals':
        manage_package_repo => true,
        version             => '4.4.2',
    }->
    class { 'mongodb::server':
        bind_ip => ['127.0.0.1'],
    }

    class { 'elastic_stack::repo':
        version => 7,
    }

    class { 'elasticsearch':
        version         => '7.10.0',
        manage_repo     => true,
        config          => {
            'cluster.name'  => 'graylog',
            'http.port'     => '9200',
            'network.host'  => '127.0.0.1',
        },
    }

    class { 'graylog::repository':
        version => '4.0',
    }->
    class { 'graylog::server':
        package_version => '4.0.1-1',
        config          => {
            'password_secret'       => lookup('passwords::graylog::password_secret'),
            'root_password_sha2'    => lookup('passwords::graylog::root_password_sha2'),
        }
    }

    # Access is restricted: https://meta.miraheze.org/wiki/Tech:Graylog#Access
    $fwHttps = query_facts("domain='$domain' and (Class[Role::Mediawiki] or Class[Role::Icinga2])", ['ipaddress', 'ipaddress6'])
    $fwHttps.each |$key, $value| {
        ufw::allow { "graylog access 443/tcp for ${value['ipaddress']}":
            proto => 'tcp',
            port  => 443,
            from  => $value['ipaddress'],
        }

        ufw::allow { "graylog access 443/tcp for ${value['ipaddress6']}":
            proto => 'tcp',
            port  => 443,
            from  => $value['ipaddress6'],
        }
    }

    # syslog-ng > graylog 12210/tcp
    $fwSyslog = query_facts("domain='$domain' and (Class[Role::Mediawiki] or Class[Role::Icinga2])", ['ipaddress', 'ipaddress6'])
    $fwSyslog.each |$key, $value| {
        ufw::allow { "graylog access 12210/tcp for ${value['ipaddress']}":
            proto => 'tcp',
            port  => 12210,
            from  => $value['ipaddress'],
        }

        ufw::allow { "graylog access 12210/tcp for ${value['ipaddress6']}":
            proto => 'tcp',
            port  => 12210,
            from  => $value['ipaddress6'],
        }
    }

    motd::role { 'role::graylog':
        description => 'central logging server',
    }
}
