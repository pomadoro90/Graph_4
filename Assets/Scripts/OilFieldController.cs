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
        public PumpjackAnimator[] pumpjackAnimators;

        private void Awake()
        {
            RefreshAnimators();
            ApplyState();
        }

        public void RefreshAnimators()
        {
            if (flowAnimators == null || flowAnimators.Length == 0)
                flowAnimators = FindObjectsOfType<FluidFlowAnimator>();
            if (pumpjackAnimators == null || pumpjackAnimators.Length == 0)
                pumpjackAnimators = FindObjectsOfType<PumpjackAnimator>();
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

        private void OnGUI()
        {
            string label = isRunning ? "Остановить анимации" : "Запустить анимации";
            if (GUI.Button(new Rect(18, 18, 210, 42), label))
                ToggleProcess();
            GUI.Label(new Rect(18, 64, 260, 24), $"Скорость: {flowSpeed:0.00}x  (+ / -)");
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
            RefreshAnimators();
            if (flowAnimators != null)
            {
                foreach (var animator in flowAnimators)
                {
                    if (animator == null) continue;
                    animator.SetRunning(isRunning);
                    animator.SetSpeed(flowSpeed);
                }
            }
            if (pumpjackAnimators != null)
            {
                foreach (var animator in pumpjackAnimators)
                {
                    if (animator == null) continue;
                    animator.SetRunning(isRunning);
                    animator.SetSpeed(flowSpeed);
                }
            }
        }
    }
}
