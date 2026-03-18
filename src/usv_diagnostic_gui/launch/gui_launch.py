from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='usv_diagnostic_gui',
            executable='usv_diagnostic_gui',
            name='usv_diagnostic_gui',
            output='screen'
        )
    ])