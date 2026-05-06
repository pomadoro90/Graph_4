#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Graph4.OilField.EditorTools
{
    public static class OilFieldSceneBuilder
    {
        [MenuItem("Graph4/Build Oil Field Demo Scene")]
        public static void BuildScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var bootstrapObject = new GameObject("Runtime Scene Bootstrap");
            var bootstrap = bootstrapObject.AddComponent<RuntimeSceneBootstrap>();
            bootstrap.groundMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/Materials/Ground_Tundra.mat");
            bootstrap.oilMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/Materials/Oil_Flow.mat");
            bootstrap.waterMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/Materials/Water_Pipe.mat");
            bootstrap.metalMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/Materials/Metal_Dark.mat");
            bootstrap.oilFieldModelPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Models/field_development_complex.fbx");

            var cameraObject = new GameObject("Main Camera");
            cameraObject.tag = "MainCamera";
            var camera = cameraObject.AddComponent<Camera>();
            camera.transform.position = new Vector3(28f, 26f, -44f);
            camera.transform.rotation = Quaternion.Euler(55f, -30f, 0f);
            cameraObject.AddComponent<CameraFlyController>();

            var sunObject = new GameObject("Sun");
            var sun = sunObject.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.25f;
            sunObject.transform.rotation = Quaternion.Euler(50f, -35f, 0f);

            Directory.CreateDirectory("Assets/Scenes");
            EditorSceneManager.SaveScene(scene, "Assets/Scenes/OilFieldDemo.unity");
            AssetDatabase.SaveAssets();
            Debug.Log("Saved Assets/Scenes/OilFieldDemo.unity. Press Play to let RuntimeSceneBootstrap generate terrain and flow controls.");
        }
    }
}
#endif
