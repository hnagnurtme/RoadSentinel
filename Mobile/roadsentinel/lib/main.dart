import 'dart:async';

import 'package:flutter/material.dart';

import 'models/app_config.dart';
import 'models/pipeline_status.dart';
import 'services/config_service.dart';
import 'services/pipeline_service.dart';

void main() {
  runApp(const RoadSentinelApp());
}

class RoadSentinelApp extends StatelessWidget {
  const RoadSentinelApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RoadSentinel Gateway Mobile',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF005B96)),
        scaffoldBackgroundColor: const Color(0xFFF5F7FA),
        useMaterial3: true,
      ),
      home: const GatewayMobilePage(),
    );
  }
}

class GatewayMobilePage extends StatefulWidget {
  const GatewayMobilePage({super.key});

  @override
  State<GatewayMobilePage> createState() => _GatewayMobilePageState();
}

class _GatewayMobilePageState extends State<GatewayMobilePage> {
  static const _supportedModelAssets = [
    'assets/models/best_float16.tflite',
    'assets/models/best_float32.tflite',
  ];

  final _configService = ConfigService();

  final _webcamUrlCtrl = TextEditingController();
  final _wsUrlCtrl = TextEditingController();
  final _httpUrlCtrl = TextEditingController();
  final _deviceIdCtrl = TextEditingController();
  final _fpsCtrl = TextEditingController();
  final _cloudNameCtrl = TextEditingController();
  final _uploadPresetCtrl = TextEditingController();
  final _cloudFolderCtrl = TextEditingController();

  bool _cloudinaryEnabled = false;
  bool _loading = true;
  String _selectedModelAssetPath = AppConfig.defaults().modelAssetPath;

  AppConfig _config = AppConfig.defaults();
  PipelineService? _pipeline;
  StreamSubscription<PipelineStatus>? _statusSub;
  PipelineStatus _status = PipelineStatus.idle();

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  @override
  void dispose() {
    _statusSub?.cancel();
    _pipeline?.dispose();
    _webcamUrlCtrl.dispose();
    _wsUrlCtrl.dispose();
    _httpUrlCtrl.dispose();
    _deviceIdCtrl.dispose();
    _fpsCtrl.dispose();
    _cloudNameCtrl.dispose();
    _uploadPresetCtrl.dispose();
    _cloudFolderCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadConfig() async {
    final config = await _configService.load();
    _config = config;

    _webcamUrlCtrl.text = config.webcamServerUrl;
    _wsUrlCtrl.text = config.wsUrl;
    _httpUrlCtrl.text = config.httpUrl;
    _deviceIdCtrl.text = config.deviceId;
    _fpsCtrl.text = config.targetFps.toString();
    _cloudNameCtrl.text = config.cloudinaryCloudName;
    _uploadPresetCtrl.text = config.cloudinaryUploadPreset;
    _cloudFolderCtrl.text = config.cloudinaryFolder;
    _cloudinaryEnabled = config.cloudinaryEnabled;
    _selectedModelAssetPath = _supportedModelAssets.contains(config.modelAssetPath)
      ? config.modelAssetPath
      : AppConfig.defaults().modelAssetPath;

    if (!mounted) {
      return;
    }

    setState(() {
      _loading = false;
    });
  }

  AppConfig _readConfigFromForm() {
    final fps = int.tryParse(_fpsCtrl.text.trim()) ?? _config.targetFps;
    return AppConfig(
      webcamServerUrl: _webcamUrlCtrl.text.trim(),
      targetFps: fps.clamp(1, 30),
      modelAssetPath: _selectedModelAssetPath,
      modelInputSize: _config.modelInputSize,
      inferenceConfidenceThreshold: _config.inferenceConfidenceThreshold,
      inferenceIouThreshold: _config.inferenceIouThreshold,
      inferenceMaxDetections: _config.inferenceMaxDetections,
      wsUrl: _wsUrlCtrl.text.trim(),
      httpUrl: _httpUrlCtrl.text.trim(),
      deviceId: _deviceIdCtrl.text.trim(),
      reconnectDelaySeconds: _config.reconnectDelaySeconds,
      queueMaxsize: _config.queueMaxsize,
      cloudinaryEnabled: _cloudinaryEnabled,
      cloudinaryCloudName: _cloudNameCtrl.text.trim(),
      cloudinaryUploadPreset: _uploadPresetCtrl.text.trim(),
      cloudinaryFolder: _cloudFolderCtrl.text.trim().isEmpty
          ? _config.cloudinaryFolder
          : _cloudFolderCtrl.text.trim(),
      unknownEnterFrames: _config.unknownEnterFrames,
      minSleepConfidence: _config.minSleepConfidence,
      minPhoneConfidence: _config.minPhoneConfidence,
      minDistractedConfidence: _config.minDistractedConfidence,
      sleepEnterFrames: _config.sleepEnterFrames,
      sleepExitFrames: _config.sleepExitFrames,
      phoneEnterFrames: _config.phoneEnterFrames,
      phoneExitFrames: _config.phoneExitFrames,
      distractedEnterFrames: _config.distractedEnterFrames,
      distractedExitFrames: _config.distractedExitFrames,
      eventPriority: _config.eventPriority,
      presenceLabels: _config.presenceLabels,
      sleepLabels: _config.sleepLabels,
      phoneLabels: _config.phoneLabels,
      distractedLabels: _config.distractedLabels,
      sleepEvidenceSeconds: _config.sleepEvidenceSeconds,
      sleepTriggerRatio: _config.sleepTriggerRatio,
      useSleepProxy: _config.useSleepProxy,
      minPresenceConfidence: _config.minPresenceConfidence,
      minEyesOpenConfidence: _config.minEyesOpenConfidence,
      labels: _config.labels,
    );
  }

  Future<void> _saveConfig() async {
    final next = _readConfigFromForm();
    await _configService.save(next);
    setState(() {
      _config = next;
    });
    _showSnack('Saved config');
  }

  Future<void> _startPipeline() async {
    await _stopPipeline();
    final next = _readConfigFromForm();
    await _configService.save(next);

    final pipeline = PipelineService(next);
    _statusSub = pipeline.statusStream.listen((status) {
      if (!mounted) {
        return;
      }
      setState(() {
        _status = status;
      });
    });

    await pipeline.start();
    setState(() {
      _config = next;
      _pipeline = pipeline;
    });
  }

  Future<void> _stopPipeline() async {
    await _statusSub?.cancel();
    _statusSub = null;
    await _pipeline?.stop();
    _pipeline = null;
  }

  void _showSnack(String text) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final running = _pipeline != null && _status.running;

    return Scaffold(
      appBar: AppBar(
        title: const Text('RoadSentinel Gateway Mobile'),
        actions: [
          IconButton(
            onPressed: _saveConfig,
            icon: const Icon(Icons.save),
            tooltip: 'Save config',
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _StatusCard(status: _status, running: running),
            const SizedBox(height: 12),
            _sectionTitle('Capture & Sender'),
            _field(_webcamUrlCtrl, 'Webcam Server URL (MJPEG)'),
            _field(_wsUrlCtrl, 'WebSocket URL'),
            _field(_httpUrlCtrl, 'HTTP Fallback URL'),
            _field(_deviceIdCtrl, 'Device ID'),
            _field(_fpsCtrl, 'Target FPS', keyboardType: TextInputType.number),
            const SizedBox(height: 6),
            _modelSelector(),
            const SizedBox(height: 12),
            _sectionTitle('Cloudinary Evidence'),
            SwitchListTile(
              value: _cloudinaryEnabled,
              title: const Text('Enable Cloudinary Upload'),
              onChanged: (v) => setState(() => _cloudinaryEnabled = v),
            ),
            _field(_cloudNameCtrl, 'Cloud name'),
            _field(_uploadPresetCtrl, 'Unsigned upload preset'),
            _field(_cloudFolderCtrl, 'Folder'),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: running ? null : _startPipeline,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start Pipeline'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: running ? _stopPipeline : null,
                    icon: const Icon(Icons.stop),
                    label: const Text('Stop'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionTitle(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }

  Widget _field(
    TextEditingController controller,
    String label, {
    TextInputType keyboardType = TextInputType.text,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        controller: controller,
        keyboardType: keyboardType,
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }

  Widget _modelSelector() {
    return DropdownButtonFormField<String>(
      initialValue: _selectedModelAssetPath,
      items: _supportedModelAssets
          .map(
            (path) => DropdownMenuItem<String>(
              value: path,
              child: Text(path.split('/').last),
            ),
          )
          .toList(growable: false),
      onChanged: (value) {
        if (value == null) {
          return;
        }
        setState(() {
          _selectedModelAssetPath = value;
        });
      },
      decoration: const InputDecoration(
        labelText: 'Model Asset',
        border: OutlineInputBorder(),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.status, required this.running});

  final PipelineStatus status;
  final bool running;

  @override
  Widget build(BuildContext context) {
    final color = switch (status.event) {
      'sleeping' => Colors.red,
      'using_phone' => Colors.orange,
      'distracted' => Colors.amber,
      'unknown' => Colors.blueGrey,
      _ => Colors.green,
    };

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  running ? Icons.circle : Icons.pause_circle,
                  color: running ? Colors.green : Colors.grey,
                ),
                const SizedBox(width: 8),
                Text(running ? 'Running' : 'Stopped'),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Event: ${status.event}',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(color: color),
            ),
            Text('Event Conf: ${status.confidence.toStringAsFixed(2)}'),
            Text('Max Det Conf: ${status.maxDetectionConfidence.toStringAsFixed(2)}'),
            Text('Detections: ${status.detectionCount}'),
            if (status.lastEvidenceUrl != null) ...[
              const SizedBox(height: 8),
              Text('Evidence: ${status.lastEvidenceUrl}'),
            ],
            if (status.lastError != null) ...[
              const SizedBox(height: 8),
              Text(
                'Error: ${status.lastError}',
                style: const TextStyle(color: Colors.red),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
