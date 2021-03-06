# role: prometheus
class role::prometheus {
    include ::prometheus

    ufw::allow { 'prometheus tcp':
        proto => 'tcp',
        port  => 9090,
        from  => '185.52.1.76',
    }

    ufw::allow { 'prometheus tcp ipv4':
        proto => 'tcp',
        port  => '9090',
        from  => '51.89.160.138',
    }

    ufw::allow { 'prometheus tcp ipv6':
        proto => 'tcp',
        port  => '9090',
        from  => '2001:41d0:800:105a::6',
    }

    motd::role { 'role::prometheus':
        description => 'central Prometheus server',
    }
}
