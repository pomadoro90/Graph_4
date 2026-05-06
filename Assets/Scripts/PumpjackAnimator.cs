using System;
using UnityEngine;

namespace Graph4.OilField
{
    /// <summary>
    /// Procedural pumpjack kinematics for imported Blender objects.
    /// The beam pivot and crankshaft are fixed; pitman length is fixed; the polished rod
    /// enters the ground at a fixed point and only changes visible suspension length.
    /// </summary>
    public class PumpjackAnimator : MonoBehaviour
    {
        [Header("State")]
        public bool running;
        [Range(0.05f, 6f)] public float speed = 1f;

        [Header("Found parts")]
        public Transform beamPivot;
        public Transform crankLeft;
        public Transform crankRight;
        public Transform[] pitmans = Array.Empty<Transform>();
        public Transform bridleCable;

        [Header("Kinematics")]
        public float beamSwingDegrees = 7.5f;
        public float cableStroke = 0.55f;

        private Quaternion beamBaseRotation;
        private Quaternion crankLeftBaseRotation;
        private Quaternion crankRightBaseRotation;
        private Vector3 cableBaseScale;
        private Vector3 cableBasePosition;
        private Vector3[] pitmanBaseScales;
        private Quaternion[] pitmanBaseRotations;
        private float phase;

        private void Awake()
        {
            AutoBindIfNeeded();
            CacheRestPose();
        }

        private void Update()
        {
            if (!running) return;
            phase += Time.deltaTime * speed * Mathf.PI * 2f / 4f;
            ApplyPose(phase);
        }

        public void SetRunning(bool value) => running = value;
        public void SetSpeed(float value) => speed = Mathf.Clamp(value, 0.05f, 6f);

        public void AutoBindIfNeeded()
        {
            string n = gameObject.name;
            if (beamPivot == null) beamPivot = FindChildContains(transform, n + "_ANIM_beam_pivot") ?? FindChildContains(transform, "ANIM_beam_pivot");
            if (crankLeft == null) crankLeft = FindChildContains(transform, n + "_ANIM_crank_L") ?? FindChildContains(transform, "ANIM_crank_L");
            if (crankRight == null) crankRight = FindChildContains(transform, n + "_ANIM_crank_R") ?? FindChildContains(transform, "ANIM_crank_R");
            if (bridleCable == null) bridleCable = FindChildContains(transform, n + "_bridle_cable") ?? FindChildContains(transform, "bridle_cable");
            if (pitmans == null || pitmans.Length == 0)
            {
                Transform l = FindChildContains(transform, n + "_pitman_L") ?? FindChildContains(transform, "pitman_L");
                Transform r = FindChildContains(transform, n + "_pitman_R") ?? FindChildContains(transform, "pitman_R");
                pitmans = l != null && r != null ? new[] { l, r } : Array.Empty<Transform>();
            }
        }

        private void CacheRestPose()
        {
            if (beamPivot != null) beamBaseRotation = beamPivot.localRotation;
            if (crankLeft != null) crankLeftBaseRotation = crankLeft.localRotation;
            if (crankRight != null) crankRightBaseRotation = crankRight.localRotation;
            if (bridleCable != null)
            {
                cableBaseScale = bridleCable.localScale;
                cableBasePosition = bridleCable.localPosition;
            }
            pitmanBaseScales = new Vector3[pitmans?.Length ?? 0];
            pitmanBaseRotations = new Quaternion[pitmans?.Length ?? 0];
            for (int i = 0; i < pitmanBaseScales.Length; i++)
            {
                if (pitmans[i] == null) continue;
                pitmanBaseScales[i] = pitmans[i].localScale;
                pitmanBaseRotations[i] = pitmans[i].localRotation;
            }
        }

        private void ApplyPose(float t)
        {
            float crank = t * Mathf.Rad2Deg;
            float beam = Mathf.Sin(t) * beamSwingDegrees;
            if (beamPivot != null)
                beamPivot.localRotation = beamBaseRotation * Quaternion.Euler(beam, 0f, 0f);
            if (crankLeft != null)
                crankLeft.localRotation = crankLeftBaseRotation * Quaternion.Euler(crank, 0f, 0f);
            if (crankRight != null)
                crankRight.localRotation = crankRightBaseRotation * Quaternion.Euler(crank, 0f, 0f);

            // Visual fixed-length pitman behaviour: rotate with crank phase but do not scale.
            for (int i = 0; i < (pitmans?.Length ?? 0); i++)
            {
                if (pitmans[i] == null) continue;
                pitmans[i].localScale = pitmanBaseScales[i];
                pitmans[i].localRotation = pitmanBaseRotations[i] * Quaternion.Euler(Mathf.Sin(t + Mathf.PI * 0.5f) * 5f, 0f, 0f);
            }

            // Only suspension length changes; its bottom/ground point remains visually fixed.
            if (bridleCable != null)
            {
                float stretch = 1f + Mathf.Sin(t) * cableStroke;
                bridleCable.localScale = new Vector3(cableBaseScale.x, cableBaseScale.y, cableBaseScale.z * Mathf.Max(0.35f, stretch));
                bridleCable.localPosition = cableBasePosition + Vector3.up * (stretch - 1f) * 0.25f;
            }
        }

        private static Transform FindChildContains(Transform root, string token)
        {
            if (root == null || string.IsNullOrEmpty(token)) return null;
            token = token.ToLowerInvariant();
            foreach (Transform child in root.GetComponentsInChildren<Transform>(true))
            {
                if (child.name.ToLowerInvariant().Contains(token)) return child;
            }
            return null;
        }
    }
}
