using UnityEngine;

namespace Graph4.OilField
{
    /// <summary>
    /// Lightweight visual flow animation. Put this on small marker objects or generated
    /// spheres inside RuntimeSceneBootstrap. The marker moves between waypoints only
    /// when OilFieldController is running.
    /// </summary>
    public class FluidFlowAnimator : MonoBehaviour
    {
        public Transform[] waypoints;
        public float speed = 1f;
        public bool running;
        public bool loop = true;

        private int currentIndex;

        private void Update()
        {
            if (!running || waypoints == null || waypoints.Length < 2)
                return;

            Transform target = waypoints[currentIndex + 1];
            transform.position = Vector3.MoveTowards(transform.position, target.position, speed * Time.deltaTime);

            if (Vector3.Distance(transform.position, target.position) <= 0.02f)
            {
                currentIndex++;
                if (currentIndex >= waypoints.Length - 1)
                {
                    if (loop)
                    {
                        currentIndex = 0;
                        transform.position = waypoints[0].position;
                    }
                    else
                    {
                        running = false;
                    }
                }
            }
        }

        public void SetRunning(bool value)
        {
            running = value;
        }

        public void SetSpeed(float value)
        {
            speed = Mathf.Max(0.05f, value);
        }
    }
}
