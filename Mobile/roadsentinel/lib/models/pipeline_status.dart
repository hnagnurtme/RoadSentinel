class PipelineStatus {
  const PipelineStatus({
    required this.running,
    required this.event,
    required this.confidence,
    required this.detectionCount,
    required this.lastUpdated,
    this.maxDetectionConfidence = 0.0,
    this.lastEvidenceUrl,
    this.lastError,
  });

  factory PipelineStatus.idle() {
    return PipelineStatus(
      running: false,
      event: 'normal',
      confidence: 0,
      detectionCount: 0,
      lastUpdated: DateTime.now(),
    );
  }

  final bool running;
  final String event;
  final double confidence;
  final double maxDetectionConfidence;
  final int detectionCount;
  final DateTime lastUpdated;
  final String? lastEvidenceUrl;
  final String? lastError;

  PipelineStatus copyWith({
    bool? running,
    String? event,
    double? confidence,
    double? maxDetectionConfidence,
    int? detectionCount,
    DateTime? lastUpdated,
    String? lastEvidenceUrl,
    String? lastError,
  }) {
    return PipelineStatus(
      running: running ?? this.running,
      event: event ?? this.event,
      confidence: confidence ?? this.confidence,
      maxDetectionConfidence: maxDetectionConfidence ?? this.maxDetectionConfidence,
      detectionCount: detectionCount ?? this.detectionCount,
      lastUpdated: lastUpdated ?? this.lastUpdated,
      lastEvidenceUrl: lastEvidenceUrl ?? this.lastEvidenceUrl,
      lastError: lastError,
    );
  }
}
