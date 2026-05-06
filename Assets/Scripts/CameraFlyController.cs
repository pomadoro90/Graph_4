using UnityEngine;

namespace Graph4.OilField
{
    /// <summary>
    /// Free-fly camera for inspecting the oil-field model.
    /// WASD/E/Q move, RMB+mouse looks around, Shift speeds up.
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class CameraFlyController : MonoBehaviour
    {
        public float moveSpeed = 12f;
        public float fastMultiplier = 3f;
        public float lookSensitivity = 2.2f;

        private float yaw;
        private float pitch;

        private void Start()
        {
            var e = transform.rotation.eulerAngles;
            yaw = e.y;
            pitch = e.x;
        }

        private void Update()
        {
            if (Input.GetMouseButton(1))
            {
                yaw += Input.GetAxis("Mouse X") * lookSensitivity;
                pitch -= Input.GetAxis("Mouse Y") * lookSensitivity;
                pitch = Mathf.Clamp(pitch, -85f, 85f);
                transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
            }

            float speed = moveSpeed * (Input.GetKey(KeyCode.LeftShift) ? fastMultiplier : 1f);
            Vector3 direction = Vector3.zero;
            direction += transform.forward * Input.GetAxisRaw("Vertical");
            direction += transform.right * Input.GetAxisRaw("Horizontal");
            if (Input.GetKey(KeyCode.E)) direction += Vector3.up;
            if (Input.GetKey(KeyCode.Q)) direction += Vector3.down;
            transform.position += direction.normalized * speed * Time.deltaTime;
        }
    }
}
