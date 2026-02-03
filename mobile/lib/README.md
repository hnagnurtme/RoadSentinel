# RoadSentinel Mobile - Cấu trúc thư mục

## 📁 Tổng quan cấu trúc

Dự án sử dụng **Clean Architecture** kết hợp với **Feature-First** organization.

```
lib/
├── core/                    # Code dùng chung toàn app
│   ├── constants/          # Hằng số (API, colors, strings...)
│   ├── utils/              # Tiện ích (logger, validators...)
│   ├── network/            # API client & interceptors
│   └── routes/             # Routing configuration
│
├── features/               # Chia theo domain (GIỐNG BACKEND)
│   ├── auth/              # Authentication feature
│   └── user/              # User management feature
│
├── shared/                # UI components & themes
│   ├── widgets/           # Reusable widgets
│   └── themes/            # App theming
│
├── main.dart              # Entry point
└── app.dart               # App configuration
```

## 🏗️ Clean Architecture Layers

Mỗi feature được chia thành 3 layers:

### 1. **Data Layer** (`data/`)
- **models/**: Data models (JSON serialization)
- **services/**: API calls
- **repositories/**: Implementation của repository interfaces

### 2. **Domain Layer** (`domain/`)
- **entities/**: Business objects (pure Dart classes)
- **repositories/**: Abstract repository interfaces
- **usecases/**: Business logic

### 3. **Presentation Layer** (`presentation/`)
- **pages/**: UI screens
- **widgets/**: Feature-specific widgets
- **bloc/**: State management (BLoC/Provider/Riverpod)

## 📦 Dependencies

### Core Dependencies
- `dio`: HTTP client cho API calls
- `intl`: Internationalization và date formatting

### State Management (chọn 1)
- `flutter_bloc`: BLoC pattern
- `provider`: Provider pattern  
- `riverpod`: Riverpod pattern

### Storage
- `shared_preferences`: Key-value storage
- `flutter_secure_storage`: Secure token storage

## 🚀 Bắt đầu

1. Install dependencies:
```bash
flutter pub get
```

2. Run app:
```bash
flutter run
```

3. Format code:
```bash
dart format .
```

## 📝 Quy tắc code

1. **Naming Convention**:
   - Files: `snake_case.dart`
   - Classes: `PascalCase`
   - Variables/Functions: `camelCase`
   - Constants: `UPPER_SNAKE_CASE` hoặc `camelCase` với `static const`

2. **Import Order**:
   ```dart
   // 1. Dart imports
   import 'dart:async';
   
   // 2. Flutter imports
   import 'package:flutter/material.dart';
   
   // 3. Package imports
   import 'package:dio/dio.dart';
   
   // 4. Project imports
   import '../models/user.dart';
   ```

3. **Feature Organization**:
   - Mỗi feature độc lập, có thể tách ra package riêng
   - Không import trực tiếp từ data layer sang presentation
   - Luôn đi qua domain layer (dependency inversion)

## 🔄 Data Flow

```
UI (Presentation) 
  ↓
UseCase (Domain)
  ↓
Repository Interface (Domain)
  ↓
Repository Implementation (Data)
  ↓
API Service (Data)
```

## 📚 Thêm feature mới

1. Tạo folder mới trong `features/`
2. Tạo 3 layers: `data/`, `domain/`, `presentation/`
3. Implement theo pattern có sẵn trong `auth/`
4. Update routes trong `core/routes/app_routes.dart`

## 🎨 Theme & Colors

- Colors: `lib/core/constants/app_colors.dart`
- Theme: `lib/shared/themes/app_theme.dart`
- Strings: `lib/core/constants/app_strings.dart`

## ⚠️ TODO

- [ ] Implement BLoC/Provider cho state management
- [ ] Add error handling & error models
- [ ] Add loading states
- [ ] Add token storage (secure_storage)
- [ ] Add refresh token logic
- [ ] Add logging service (production)
- [ ] Add environment config (dev/staging/prod)
- [ ] Add integration tests
- [ ] Add code generation (freezed, json_serializable)
