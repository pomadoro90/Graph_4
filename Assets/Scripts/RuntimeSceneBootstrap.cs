using UnityEngine;

namespace Graph4.OilField
{
    /// <summary>
    /// Creates a usable Unity scene at runtime when the repository is opened without
    /// a pre-authored .unity scene: terrain, lights, camera, imported model and
    /// animated flow markers.
    /// </summary>
    public class RuntimeSceneBootstrap : MonoBehaviour
    {
        public GameObject oilFieldModelPrefab;
        public Material groundMaterial;
        public Material oilMaterial;
        public Material waterMaterial;
        public Material metalMaterial;

        private void Start()
        {
            EnsureLighting();
            EnsureTerrain();
            EnsureCamera();
            GameObject field = EnsureOilFieldModel();
            CreateFlowDemo(field != null ? field.transform : null);
        }

        private void EnsureLighting()
        {
            if (FindObjectOfType<Light>() == null)
            {
                var sunObject = new GameObject("Sun");
                var sun = sunObject.AddComponent<Light>();
                sun.type = LightType.Directional;
                sun.intensity = 1.25f;
                sunObject.transform.rotation = Quaternion.Euler(50f, -35f, 0f);
            }
            RenderSettings.ambientLight = new Color(0.55f, 0.58f, 0.62f);
        }

        private void EnsureTerrain()
        {
            if (FindObjectOfType<Terrain>() != null) return;

            TerrainData data = new TerrainData
            {
                heightmapResolution = 129,
                size = new Vector3(180f, 8f, 140f)
            };
            float[,] heights = new float[data.heightmapResolution, data.heightmapResolution];
            for (int y = 0; y < data.heightmapResolution; y++)
            for (int x = 0; x < data.heightmapResolution; x++)
            {
                float nx = x / 18.0f;
                float ny = y / 23.0f;
                heights[y, x] = Mathf.PerlinNoise(nx, ny) * 0.035f;
            }
            data.SetHeights(0, 0, heights);
            Terrain terrain = Terrain.CreateTerrainGameObject(data).GetComponent<Terrain>();
            terrain.name = "Generated tundra terrain";
            terrain.transform.position = new Vector3(-90f, -0.08f, -70f);
            if (groundMaterial != null) terrain.materialTemplate = groundMaterial;
        }

        private void EnsureCamera()
        {
            Camera cam = Camera.main;
            if (cam == null)
            {
                var cameraObject = new GameObject("Main Camera");
                cam = cameraObject.AddComponent<Camera>();
                cameraObject.tag = "MainCamera";
            }
            cam.transform.position = new Vector3(28f, 26f, -44f);
            cam.transform.rotation = Quaternion.Euler(55f, -30f, 0f);
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 600f;
            if (cam.GetComponent<CameraFlyController>() == null)
                cam.gameObject.AddComponent<CameraFlyController>();
        }

        private GameObject EnsureOilFieldModel()
        {
            GameObject field = GameObject.Find("field_development_complex");
            if (field == null && oilFieldModelPrefab != null)
            {
                field = Instantiate(oilFieldModelPrefab, Vector3.zero, Quaternion.identity);
                field.name = "field_development_complex";
            }
            if (field != null)
            {
                field.transform.localScale = Vector3.one;
                ApplyMaterialHints(field);
            }
            return field;
        }

        private void ApplyMaterialHints(GameObject root)
        {
            if (root == null) return;
            foreach (Renderer renderer in root.GetComponentsInChildren<Renderer>())
            {
                string n = renderer.name.ToLowerInvariant();
                if ((n.Contains("water") || n.Contains("bkns") || n.Contains("kns")) && waterMaterial != null)
                    renderer.sharedMaterial = waterMaterial;
                else if ((n.Contains("pipe") || n.Contains("well") || n.Contains("vessel")) && metalMaterial != null)
                    renderer.sharedMaterial = metalMaterial;
                else if (n.Contains("oil") && oilMaterial != null)
                    renderer.sharedMaterial = oilMaterial;
            }
        }

        private void CreateFlowDemo(Transform parent)
        {
            if (FindObjectOfType<OilFieldController>() != null) return;

            var controllerObject = new GameObject("Oil Field Controller");
            var controller = controllerObject.AddComponent<OilFieldController>();

            Vector3[] path =
            {
                new Vector3(-22f, 1.2f, -9f),
                new Vector3(-13f, 1.4f, -6f),
                new Vector3(-6f, 1.7f, -1f),
                new Vector3(5f, 1.7f, 0f),
                new Vector3(17f, 1.8f, 0f),
                new Vector3(29f, 1.8f, -4f)
            };

            var waypointRoot = new GameObject("Flow waypoints").transform;
            if (parent != null) waypointRoot.SetParent(parent, false);
            Transform[] waypoints = new Transform[path.Length];
            for (int i = 0; i < path.Length; i++)
            {
                var w = new GameObject("Flow waypoint " + i).transform;
                w.SetParent(waypointRoot, false);
                w.position = path[i];
                waypoints[i] = w;
            }

            var marker = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            marker.name = "Animated fluid marker";
            marker.transform.localScale = Vector3.one * 0.55f;
            marker.transform.position = waypoints[0].position;
            if (oilMaterial != null) marker.GetComponent<Renderer>().material = oilMaterial;
            var animator = marker.AddComponent<FluidFlowAnimator>();
            animator.waypoints = waypoints;
            animator.speed = controller.flowSpeed;
            controller.flowAnimators = new[] { animator };
        }
    }
}
