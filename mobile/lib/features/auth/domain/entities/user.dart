class User {
  final String id;
  final String email;
  final String? name;
  final String? avatar;

  User({required this.id, required this.email, this.name, this.avatar});

  User copyWith({String? id, String? email, String? name, String? avatar}) {
    return User(
      id: id ?? this.id,
      email: email ?? this.email,
      name: name ?? this.name,
      avatar: avatar ?? this.avatar,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;

    return other is User &&
        other.id == id &&
        other.email == email &&
        other.name == name &&
        other.avatar == avatar;
  }

  @override
  int get hashCode {
    return id.hashCode ^ email.hashCode ^ name.hashCode ^ avatar.hashCode;
  }

  @override
  String toString() {
    return 'User(id: $id, email: $email, name: $name, avatar: $avatar)';
  }
}
