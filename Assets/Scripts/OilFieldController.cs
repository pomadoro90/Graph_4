using UnityEngine;

namespace Graph4.OilField
{
    /// <summary>
    /// Central runtime controller for the oil-field demo. Attach to an empty GameObject
    /// or let RuntimeSceneBootstrap create it automatically.
    /// </summary>
    public class OilFieldController : MonoBehaviour
    {
        [Header("Controls")]
        public KeyCode toggleKey = KeyCode.Space;
        public KeyCode fasterKey = KeyCode.Equals;
        public KeyCode slowerKey = KeyCode.Minus;

        [Header("Process state")]
        public bool isRunning;
        [Range(0.05f, 6f)] public float flowSpeed = 1f;
        public FluidFlowAnimator[] flowAnimators;

        private void Awake()
        {
            if (flowAnimators == null || flowAnimators.Length == 0)
                flowAnimators = FindObjectsOfType<FluidFlowAnimator>();
            ApplyState();
        }

        private void Update()
        {
            if (Input.GetKeyDown(toggleKey) || Input.GetMouseButtonDown(0))
                ToggleProcess();

            if (Input.GetKeyDown(fasterKey))
                SetSpeed(flowSpeed * 1.25f);

            if (Input.GetKeyDown(slowerKey))
                SetSpeed(flowSpeed / 1.25f);
        }

        public void ToggleProcess()
        {
            isRunning = !isRunning;
            ApplyState();
        }

        public void StartProcess()
        {
            isRunning = true;
            ApplyState();
        }

        public void StopProcess()
        {
            isRunning = false;
            ApplyState();
        }

        public void SetSpeed(float newSpeed)
        {
            flowSpeed = Mathf.Clamp(newSpeed, 0.05f, 6f);
            ApplyState();
        }

        private void ApplyState()
        {
            if (flowAnimators == null) return;
            foreach (var animator in flowAnimators)
            {
                if (animator == null) continue;
                animator.SetRunning(isRunning);
                animator.SetSpeed(flowSpeed);
            }
        }
    }
}
