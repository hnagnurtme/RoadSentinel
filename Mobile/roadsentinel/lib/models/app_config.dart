class AppConfig {
  AppConfig({
    required this.webcamServerUrl,
    required this.targetFps,
    required this.modelAssetPath,
    required this.modelInputSize,
    required this.inferenceConfidenceThreshold,
    required this.inferenceIouThreshold,
    required this.inferenceMaxDetections,
    required this.wsUrl,
    required this.httpUrl,
    required this.deviceId,
    required this.reconnectDelaySeconds,
    required this.queueMaxsize,
    required this.cloudinaryEnabled,
    required this.cloudinaryCloudName,
    required this.cloudinaryUploadPreset,
    required this.cloudinaryFolder,
    required this.unknownEnterFrames,
    required this.minSleepConfidence,
    required this.minPhoneConfidence,
    required this.minDistractedConfidence,
    required this.sleepEnterFrames,
    required this.sleepExitFrames,
    required this.phoneEnterFrames,
    required this.phoneExitFrames,
    required this.distractedEnterFrames,
    required this.distractedExitFrames,
    required this.eventPriority,
    required this.presenceLabels,
    required this.sleepLabels,
    required this.phoneLabels,
    required this.distractedLabels,
    required this.sleepEvidenceSeconds,
    required this.sleepTriggerRatio,
    required this.useSleepProxy,
    required this.minPresenceConfidence,
    required this.minEyesOpenConfidence,
    required this.labels,
  });

  factory AppConfig.defaults() {
    return AppConfig(
      webcamServerUrl: 'http://192.168.1.100/stream',
      targetFps: 5,
      modelAssetPath: 'assets/models/best_float16.tflite',
      modelInputSize: 320,
      inferenceConfidenceThreshold: 0.5,
      inferenceIouThreshold: 0.45,
      inferenceMaxDetections: 100,
      wsUrl: 'ws://localhost:8000/ws/gateway',
      httpUrl: 'http://localhost:8000/api/events',
      deviceId: 'car_01',
      reconnectDelaySeconds: 3,
      queueMaxsize: 200,
      cloudinaryEnabled: false,
      cloudinaryCloudName: '',
      cloudinaryUploadPreset: '',
      cloudinaryFolder: 'roadsentinel/gateway',
      unknownEnterFrames: 12,
      minSleepConfidence: 0.6,
      minPhoneConfidence: 0.6,
      minDistractedConfidence: 0.6,
      sleepEnterFrames: 6,
      sleepExitFrames: 3,
      phoneEnterFrames: 3,
      phoneExitFrames: 1,
      distractedEnterFrames: 4,
      distractedExitFrames: 2,
      eventPriority: const ['using_phone', 'sleeping', 'distracted'],
      presenceLabels: const ['face', 'eye', 'person', 'driver'],
      sleepLabels: const ['sleeping', 'drowsy', 'eyes closed', 'yawning'],
      phoneLabels: const [
        'cell phone',
        'mobile',
        'texting',
        'driver talking on phone',
      ],
      distractedLabels: const [
        'distracted',
        'driver looking away',
        'driver reaching behind',
      ],
      sleepEvidenceSeconds: 8,
      sleepTriggerRatio: 0.6,
      useSleepProxy: true,
      minPresenceConfidence: 0.4,
      minEyesOpenConfidence: 0.6,
      labels: const [
        'face',
        'eye',
        'person',
        'driver',
        'sleeping',
        'drowsy',
        'eyes closed',
        'yawning',
        'cell phone',
        'mobile',
        'texting',
        'driver talking on phone',
        'distracted',
        'driver looking away',
        'driver reaching behind',
        'eyes open',
      ],
    );
  }

  final String webcamServerUrl;
  final int targetFps;
  final String modelAssetPath;
  final int modelInputSize;
  final double inferenceConfidenceThreshold;
  final double inferenceIouThreshold;
  final int inferenceMaxDetections;

  final String wsUrl;
  final String httpUrl;
  final String deviceId;
  final int reconnectDelaySeconds;
  final int queueMaxsize;

  final bool cloudinaryEnabled;
  final String cloudinaryCloudName;
  final String cloudinaryUploadPreset;
  final String cloudinaryFolder;

  final int unknownEnterFrames;
  final double minSleepConfidence;
  final double minPhoneConfidence;
  final double minDistractedConfidence;

  final int sleepEnterFrames;
  final int sleepExitFrames;
  final int phoneEnterFrames;
  final int phoneExitFrames;
  final int distractedEnterFrames;
  final int distractedExitFrames;

  final List<String> eventPriority;
  final List<String> presenceLabels;
  final List<String> sleepLabels;
  final List<String> phoneLabels;
  final List<String> distractedLabels;

  final int sleepEvidenceSeconds;
  final double sleepTriggerRatio;
  final bool useSleepProxy;
  final double minPresenceConfidence;
  final double minEyesOpenConfidence;
  final List<String> labels;

  Map<String, dynamic> toJson() {
    return {
      'webcamServerUrl': webcamServerUrl,
      'targetFps': targetFps,
      'modelAssetPath': modelAssetPath,
      'modelInputSize': modelInputSize,
      'inferenceConfidenceThreshold': inferenceConfidenceThreshold,
      'inferenceIouThreshold': inferenceIouThreshold,
      'inferenceMaxDetections': inferenceMaxDetections,
      'wsUrl': wsUrl,
      'httpUrl': httpUrl,
      'deviceId': deviceId,
      'reconnectDelaySeconds': reconnectDelaySeconds,
      'queueMaxsize': queueMaxsize,
      'cloudinaryEnabled': cloudinaryEnabled,
      'cloudinaryCloudName': cloudinaryCloudName,
      'cloudinaryUploadPreset': cloudinaryUploadPreset,
      'cloudinaryFolder': cloudinaryFolder,
      'unknownEnterFrames': unknownEnterFrames,
      'minSleepConfidence': minSleepConfidence,
      'minPhoneConfidence': minPhoneConfidence,
      'minDistractedConfidence': minDistractedConfidence,
      'sleepEnterFrames': sleepEnterFrames,
      'sleepExitFrames': sleepExitFrames,
      'phoneEnterFrames': phoneEnterFrames,
      'phoneExitFrames': phoneExitFrames,
      'distractedEnterFrames': distractedEnterFrames,
      'distractedExitFrames': distractedExitFrames,
      'eventPriority': eventPriority,
      'presenceLabels': presenceLabels,
      'sleepLabels': sleepLabels,
      'phoneLabels': phoneLabels,
      'distractedLabels': distractedLabels,
      'sleepEvidenceSeconds': sleepEvidenceSeconds,
      'sleepTriggerRatio': sleepTriggerRatio,
      'useSleepProxy': useSleepProxy,
      'minPresenceConfidence': minPresenceConfidence,
      'minEyesOpenConfidence': minEyesOpenConfidence,
      'labels': labels,
    };
  }

  factory AppConfig.fromJson(Map<String, dynamic> json) {
    final defaults = AppConfig.defaults();
    return AppConfig(
      webcamServerUrl: json['webcamServerUrl'] as String? ?? defaults.webcamServerUrl,
      targetFps: (json['targetFps'] as num?)?.toInt() ?? defaults.targetFps,
      modelAssetPath: json['modelAssetPath'] as String? ?? defaults.modelAssetPath,
      modelInputSize: (json['modelInputSize'] as num?)?.toInt() ?? defaults.modelInputSize,
        inferenceConfidenceThreshold:
          (json['inferenceConfidenceThreshold'] as num?)?.toDouble() ??
            defaults.inferenceConfidenceThreshold,
        inferenceIouThreshold:
          (json['inferenceIouThreshold'] as num?)?.toDouble() ??
            defaults.inferenceIouThreshold,
        inferenceMaxDetections:
          (json['inferenceMaxDetections'] as num?)?.toInt() ??
            defaults.inferenceMaxDetections,
      wsUrl: json['wsUrl'] as String? ?? defaults.wsUrl,
      httpUrl: json['httpUrl'] as String? ?? defaults.httpUrl,
      deviceId: json['deviceId'] as String? ?? defaults.deviceId,
      reconnectDelaySeconds:
          (json['reconnectDelaySeconds'] as num?)?.toInt() ?? defaults.reconnectDelaySeconds,
      queueMaxsize: (json['queueMaxsize'] as num?)?.toInt() ?? defaults.queueMaxsize,
      cloudinaryEnabled:
          json['cloudinaryEnabled'] as bool? ?? defaults.cloudinaryEnabled,
      cloudinaryCloudName:
          json['cloudinaryCloudName'] as String? ?? defaults.cloudinaryCloudName,
      cloudinaryUploadPreset:
          json['cloudinaryUploadPreset'] as String? ?? defaults.cloudinaryUploadPreset,
      cloudinaryFolder:
          json['cloudinaryFolder'] as String? ?? defaults.cloudinaryFolder,
      unknownEnterFrames:
          (json['unknownEnterFrames'] as num?)?.toInt() ?? defaults.unknownEnterFrames,
      minSleepConfidence:
          (json['minSleepConfidence'] as num?)?.toDouble() ?? defaults.minSleepConfidence,
      minPhoneConfidence:
          (json['minPhoneConfidence'] as num?)?.toDouble() ?? defaults.minPhoneConfidence,
      minDistractedConfidence: (json['minDistractedConfidence'] as num?)?.toDouble() ??
          defaults.minDistractedConfidence,
      sleepEnterFrames:
          (json['sleepEnterFrames'] as num?)?.toInt() ?? defaults.sleepEnterFrames,
      sleepExitFrames:
          (json['sleepExitFrames'] as num?)?.toInt() ?? defaults.sleepExitFrames,
      phoneEnterFrames:
          (json['phoneEnterFrames'] as num?)?.toInt() ?? defaults.phoneEnterFrames,
      phoneExitFrames:
          (json['phoneExitFrames'] as num?)?.toInt() ?? defaults.phoneExitFrames,
      distractedEnterFrames: (json['distractedEnterFrames'] as num?)?.toInt() ??
          defaults.distractedEnterFrames,
      distractedExitFrames: (json['distractedExitFrames'] as num?)?.toInt() ??
          defaults.distractedExitFrames,
      eventPriority: _toStringList(json['eventPriority'], defaults.eventPriority),
      presenceLabels: _toStringList(json['presenceLabels'], defaults.presenceLabels),
      sleepLabels: _toStringList(json['sleepLabels'], defaults.sleepLabels),
      phoneLabels: _toStringList(json['phoneLabels'], defaults.phoneLabels),
      distractedLabels: _toStringList(json['distractedLabels'], defaults.distractedLabels),
      sleepEvidenceSeconds:
          (json['sleepEvidenceSeconds'] as num?)?.toInt() ?? defaults.sleepEvidenceSeconds,
      sleepTriggerRatio:
          (json['sleepTriggerRatio'] as num?)?.toDouble() ?? defaults.sleepTriggerRatio,
      useSleepProxy: json['useSleepProxy'] as bool? ?? defaults.useSleepProxy,
      minPresenceConfidence: (json['minPresenceConfidence'] as num?)?.toDouble() ??
          defaults.minPresenceConfidence,
      minEyesOpenConfidence: (json['minEyesOpenConfidence'] as num?)?.toDouble() ??
          defaults.minEyesOpenConfidence,
      labels: _toStringList(json['labels'], defaults.labels),
    );
  }

  static List<String> _toStringList(dynamic value, List<String> fallback) {
    if (value is List) {
      return value.whereType<String>().toList(growable: false);
    }
    return List<String>.from(fallback, growable: false);
  }
}
