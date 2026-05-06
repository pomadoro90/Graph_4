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
        public KeyCode fasterKeyAlt = KeyCode.KeypadPlus;
        public KeyCode slowerKey = KeyCode.Minus;
        public KeyCode slowerKeyAlt = KeyCode.KeypadMinus;
        public KeyCode resetKey = KeyCode.R;

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

            if (Input.GetKeyDown(fasterKey) || Input.GetKeyDown(fasterKeyAlt))
                SetSpeed(flowSpeed * 1.25f);

            if (Input.GetKeyDown(slowerKey) || Input.GetKeyDown(slowerKeyAlt))
                SetSpeed(flowSpeed / 1.25f);

            if (Input.GetKeyDown(resetKey))
                ResetAnimations();
        }

        private void OnGUI()
        {
            string label = isRunning ? "Остановить анимации" : "Запустить анимации";
            const float x = 18f;
            if (GUI.Button(new Rect(x, 18, 220, 42), label))
                ToggleProcess();
            if (GUI.Button(new Rect(x, 68, 105, 34), "Медленнее"))
                SetSpeed(flowSpeed / 1.25f);
            if (GUI.Button(new Rect(x + 115, 68, 105, 34), "Быстрее"))
                SetSpeed(flowSpeed * 1.25f);
            if (GUI.Button(new Rect(x, 110, 220, 34), "Сбросить движение"))
                ResetAnimations();
            GUI.Box(new Rect(x, 154, 330, 92),
                $"Управление:\n" +
                $"Space / ЛКМ — запуск/стоп\n" +
                $"+ / - — скорость: {flowSpeed:0.00}x\n" +
                $"R — сброс анимаций");
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

        public void ResetAnimations()
        {
            if (flowAnimators != null)
            {
                foreach (var animator in flowAnimators)
                {
                    if (animator == null) continue;
                    animator.ResetAnimation();
                }
            }
            if (pumpjackAnimators != null)
            {
                foreach (var animator in pumpjackAnimators)
                {
                    if (animator == null) continue;
                    animator.ResetAnimation();
                }
            }
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
