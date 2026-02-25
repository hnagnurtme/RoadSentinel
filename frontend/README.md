# RoadSentinel - Frontend Web App

Modern React application built with Vite, TypeScript, and Tailwind CSS.

## 🚀 Tech Stack

### Core
- **Vite** - Lightning-fast build tool with HMR
- **React 18** - UI library with modern hooks
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first CSS framework

### Libraries
- **React Router** - Client-side routing
- **Zustand** - Lightweight state management
- **React Query** - Data fetching and caching
- **Axios** - HTTP client with interceptors
- **React Hook Form** - Performant form handling
- **Zod** - Schema validation
- **Lucide React** - Modern icon library

## 📁 Project Structure

```
src/
├── components/     # Reusable UI components
│   ├── Button.tsx
│   ├── Card.tsx
│   └── Navbar.tsx
├── pages/          # Page components
│   ├── Home.tsx
│   └── About.tsx
├── hooks/          # Custom React hooks
│   └── useDebounce.ts
├── utils/          # Utility functions
│   └── constants.ts
├── services/       # API services
│   └── api.ts
├── store/          # State management
│   └── authStore.ts
├── types/          # TypeScript definitions
│   └── index.ts
├── assets/         # Static assets
└── styles/         # Global styles
```

## 🛠️ Getting Started

### Install Dependencies
```bash
npm install
```


## 🔧 Configuration

### Path Aliases
The project uses `@/` as an alias for the `src/` directory:
```tsx
import { Button } from '@/components/Button';
```

### Environment Variables
Create a `.env` file:
```env
VITE_API_URL=http://localhost:3000/api
```

## 📝 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 🎯 Next Steps

1. Configure your API endpoint in `.env`
2. Add your pages to `src/pages/`
3. Create reusable components in `src/components/`
4. Set up authentication using the provided `authStore`
5. Add your API services in `src/services/`

## 📚 Learn More

- [Vite Documentation](https://vite.dev/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [React Router](https://reactrouter.com/)
- [Zustand](https://github.com/pmndrs/zustand)
