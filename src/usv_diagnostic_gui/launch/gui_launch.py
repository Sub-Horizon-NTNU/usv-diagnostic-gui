from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('septentrio_host', default_value='192.168.2.6'),
        DeclareLaunchArgument('septentrio_port', default_value='29001'),
        DeclareLaunchArgument('pi_ip',           default_value='192.168.2.5'),
        DeclareLaunchArgument('pi_udp_port',     default_value='5600'),
        DeclareLaunchArgument('pi_servo_port',   default_value='5601'),
        DeclareLaunchArgument('mikrotik_user',   default_value='admin'),
        DeclareLaunchArgument('mikrotik_pass',   default_value='admin'),
        Node(
            package='usv_diagnostic_gui',
            executable='usv_diagnostic_gui',
            name='usv_diagnostic_gui',
            output='screen'
        ),
        Node(
            package='usv_diagnostic_gui',
            executable='usv_pi_interface',
            name='usv_pi_interface',
            output='screen',
            parameters=[{
                'pi_ip':      LaunchConfiguration('pi_ip'),
                'udp_port':   LaunchConfiguration('pi_udp_port'),
                'servo_port': LaunchConfiguration('pi_servo_port'),
            }]
        ),
        Node(
            package='usv_diagnostic_gui',
            executable='mikrotik_monitor',
            name='mikrotik_monitor',
            output='screen',
            parameters=[{
                'land_ip':  '192.168.2.3',
                'boat_ip':  '192.168.2.4',
                'username': LaunchConfiguration('mikrotik_user'),
                'password': LaunchConfiguration('mikrotik_pass'),
                'interface': 'wlan1',
            }]
        ),
        Node(
            package='usv_diagnostic_gui',
            executable='usv_external_pinger',
            name='usv_external_pinger',
            output='screen'
        ),
        Node(
            package='usv_diagnostic_gui',
            executable='septentrio_nmea_parser',
            name='septentrio_nmea_parser',
            output='screen',
            parameters=[{
                'host': LaunchConfiguration('septentrio_host'),
                'port': LaunchConfiguration('septentrio_port'),
            }]
        ),
    ])