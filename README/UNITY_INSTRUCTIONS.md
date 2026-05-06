# Unity-инструкции для Graph_4

В репозиторий добавлен Unity-совместимый каркас проекта и экспорт модели нефтепромысловой площадки.

## Состав

- `Assets/Models/field_development_complex.fbx` — экспорт из Blender для Unity.
- `Assets/Materials/*.mat` — базовые материалы земли, металла, воды, нефти и резервуаров.
- `Assets/Scripts/OilFieldController.cs` — запуск/останов процесса сбора нефти, управление скоростью.
- `Assets/Scripts/FluidFlowAnimator.cs` — анимация маркера потока по трубопроводам.
- `Assets/Scripts/CameraFlyController.cs` — свободная камера для осмотра объекта.
- `Assets/Scripts/RuntimeSceneBootstrap.cs` — runtime-сборка окружения: Terrain, свет, камера, модель, маркеры потока.
- `Assets/Editor/OilFieldSceneBuilder.cs` — пункт меню Unity для создания сцены `Assets/Scenes/OilFieldDemo.unity`.

## Как открыть

1. Установить Unity 2021 LTS/2022 LTS или новее.
2. В Unity Hub выбрать **Open** и указать корень репозитория `Graph_4`.
3. Дождаться импорта Assets.
4. В меню Unity выполнить **Graph4 → Build Oil Field Demo Scene**.
5. Открыть/оставить созданную сцену `Assets/Scenes/OilFieldDemo.unity` и нажать **Play**.

Если сцена не была создана через меню, можно вручную создать пустой объект `Runtime Scene Bootstrap`, добавить на него компонент `RuntimeSceneBootstrap` и назначить:

- `Oil Field Model Prefab`: `Assets/Models/field_development_complex.fbx`
- `Ground Material`: `Assets/Materials/Ground_Tundra.mat`
- `Oil Material`: `Assets/Materials/Oil_Flow.mat`
- `Water Material`: `Assets/Materials/Water_Pipe.mat`
- `Metal Material`: `Assets/Materials/Metal_Dark.mat`

## Управление в Play Mode

- `Space` или левый клик мыши — запуск/останов процесса сбора нефти.
- `=` / `+` — увеличить скорость движения потока.
- `-` — уменьшить скорость движения потока.
- `WASD` — движение камеры.
- `Q` / `E` — вниз/вверх.
- Правая кнопка мыши + движение мыши — поворот камеры.
- `Left Shift` — ускоренное движение камеры.

## Примечание

В этой cron-среде Unity Editor CLI не обнаружен, поэтому полноценная `.unity`-сцена не была сгенерирована редактором. Вместо этого подготовлен самодостаточный каркас: Unity при открытии проекта импортирует FBX, материалы и C#-скрипты, а сцена создаётся через editor-меню или runtime bootstrap.
