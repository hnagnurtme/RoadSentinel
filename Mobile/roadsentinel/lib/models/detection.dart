class Detection {
  Detection({
    required this.label,
    required this.classId,
    required this.confidence,
    required this.bbox,
  });

  final String label;
  final int classId;
  final double confidence;
  final List<double> bbox;
}
