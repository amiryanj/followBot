#!/usr/bin/env python

import rospy
from followbot.followbot_sim_ros import run_sim

if __name__ == '__main__':
    rospy.init_node('followbot_sim')
    try:
        run_sim()
        # talker()
    except rospy.ROSInterruptException:
        pass
    rospy.spin()