# @summary
#   This class handles the Kafka (consumer).
#
# @example Basic usage
#   class { 'kafka::consumer':
#     config => {
#       'client.id'         => '0',
#       'zookeeper.connect' => 'localhost:2181'
#     }
#   }
#
# @param kafka_version
#   The version of Kafka that should be installed.
#
# @param scala_version
#   The scala version what Kafka was built with.
#
# @param install_dir
#   The directory to install Kafka to.
#
# @param mirror_url
#   The url where the Kafka is downloaded from.
#
# @param manage_java
#   Install java if it's not already installed.
#
# @param package_dir
#   The directory to install Kafka.
#
# @param package_name
#   Package name, when installing Kafka from a package.
#
# @param package_ensure
#   Package version or ensure state, when installing Kafka from a package.
#
# @param user_name
#   User to run Kafka as.
#
# @param user_shell
#   Login shell of the Kafka user.
#
# @param group_name
#   Group to run Kafka as.
#
# @param user_id
#   Create the Kafka user with this ID.
#
# @param group_id
#   Create the Kafka group with this ID.
#
# @param manage_user
#   Create the Kafka user if it's not already present.
#
# @param manage_group
#   Create the Kafka group if it's not already present.
#
# @param config_mode
#   The permissions for the config files.
#
# @param config_dir
#   The directory to create the Kafka config files to.
#
# @param log_dir
#   The directory for Kafka log files.
#
# @param bin_dir
#   The directory where the Kafka scripts are.
#
# @param service_name
#   Set the name of the service.
#
# @param manage_service
#   Install the init.d or systemd service.
#
# @param service_ensure
#   Set the ensure state of the service.
#
# @param service_restart
#   Whether the configuration files should trigger a service restart.
#
# @param service_requires
#   Set the list of services required to be running before Kafka.
#
# @param limit_nofile
#   Set the 'LimitNOFILE' option of the systemd service.
#
# @param limit_core
#   Set the 'LimitCORE' option of the systemd service.
#
# @param env
#   A hash of the environment variables to set.
#
# @param config
#   A hash of the consumer configuration options.
#
# @param service_config
#   A hash of the `kafka-console-consumer.sh` script options.
#
# @param jmx_opts
#   Set the JMX options.
#
# @param log4j_opts
#   Set the Log4j options.
#
class kafka::consumer (
  String[1] $kafka_version                      = $kafka::params::kafka_version,
  String[1] $scala_version                      = $kafka::params::scala_version,
  Stdlib::Absolutepath $install_dir             = $kafka::params::install_dir,
  Stdlib::HTTPUrl $mirror_url                   = $kafka::params::mirror_url,
  Boolean $manage_java                          = $kafka::params::manage_java,
  Stdlib::Absolutepath $package_dir             = $kafka::params::package_dir,
  Optional[String[1]] $package_name             = $kafka::params::package_name,
  String[1] $package_ensure                     = $kafka::params::package_ensure,
  String[1] $user_name                          = $kafka::params::user_name,
  Stdlib::Absolutepath $user_shell              = $kafka::params::user_shell,
  String[1] $group_name                         = $kafka::params::group_name,
  Optional[Integer] $user_id                    = $kafka::params::user_id,
  Optional[Integer] $group_id                   = $kafka::params::group_id,
  Boolean $manage_user                          = $kafka::params::manage_user,
  Boolean $manage_group                         = $kafka::params::manage_group,
  Stdlib::Filemode $config_mode                 = $kafka::params::config_mode,
  Stdlib::Absolutepath $config_dir              = $kafka::params::config_dir,
  Stdlib::Absolutepath $log_dir                 = $kafka::params::log_dir,
  Stdlib::Absolutepath $bin_dir                 = $kafka::params::bin_dir,
  String[1] $service_name                       = 'kafka-consumer',
  Boolean $manage_service                       = $kafka::params::manage_service,
  Enum['running', 'stopped'] $service_ensure    = $kafka::params::service_ensure,
  Boolean $service_restart                      = $kafka::params::service_restart,
  Array[String[1]] $service_requires            = $kafka::params::service_requires,
  Optional[String[1]] $limit_nofile             = $kafka::params::limit_nofile,
  Optional[String[1]] $limit_core               = $kafka::params::limit_core,
  Hash $env                                     = {},
  Hash[String[1], Any] $config                  = {},
  Hash[String[1],String[1]] $service_config     = {},
  String[1] $jmx_opts                           = $kafka::params::consumer_jmx_opts,
  String[1] $log4j_opts                         = $kafka::params::consumer_log4j_opts,
  Boolean $manage_log4j                         = $kafka::params::manage_log4j,
  Pattern[/[1-9][0-9]*[KMG]B/] $log_file_size   = $kafka::params::log_file_size,
  Integer[1, 50] $log_file_count                = $kafka::params::log_file_count
) inherits kafka::params {
  class { 'kafka::consumer::install': }
  -> class { 'kafka::consumer::config': }
  -> class { 'kafka::consumer::service': }
  -> Class['kafka::consumer']
}
