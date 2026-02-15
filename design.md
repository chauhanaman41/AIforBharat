# Design Document: AIforBharat Frontend Architecture

## Overview

The AIforBharat Frontend Architecture is a modern, scalable React application built with TypeScript, Vite, and Tailwind CSS. The system implements a component-based architecture with clear separation of concerns, efficient state management using React Context, and robust data fetching strategies with caching. The design prioritizes performance, accessibility, type safety, and developer experience.

### Key Design Principles

1. **Component Modularity**: Atomic design hierarchy ensuring reusable, composable components
2. **Type Safety First**: Strict TypeScript configuration catching errors at compile time
3. **Performance by Default**: Code splitting, lazy loading, and optimized rendering strategies
4. **Accessibility Built-in**: WCAG 2.1 AA compliance from the ground up
5. **Developer Experience**: Fast builds, hot module replacement, and clear code patterns

### Technology Stack

- **Runtime**: Node.js v20.x LTS
- **Package Manager**: pnpm v8+
- **Framework**: React 19.2.0
- **Build Tool**: Vite 7.2.4
- **Language**: TypeScript 5.x (Strict Mode)
- **Styling**: Tailwind CSS 3.4.17
- **Routing**: React Router DOM 7.13.0
- **Form Management**: react-hook-form + zod
- **Testing**: Vitest + React Testing Library + Playwright
- **Linting**: ESLint 9.x + Prettier

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Client)                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              React Application Layer                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │   Pages      │  │  Templates   │  │  Organisms  │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │  Molecules   │  │    Atoms     │  │   Hooks     │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              State Management Layer                     │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │ Auth Context │  │ WebSocket    │  │ Cache Layer │  │ │
│  │  │              │  │ Provider     │  │             │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Service Layer                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │ Auth Service │  │ API Client   │  │ WebSocket   │  │ │
│  │  │              │  │ (Axios)      │  │ Client      │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS / WSS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  /api/auth/*  │  /api/data/*  │  /ws/*  │  /refresh   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    Backend Services & Database
```

### Component Architecture

The application follows atomic design principles with five levels of component hierarchy:

1. **Atoms**: Basic building blocks (Button, Input, Label, Icon)
2. **Molecules**: Simple combinations of atoms (FormField, SearchBar, Card)
3. **Organisms**: Complex components (Header, Sidebar, DataTable, LoginForm)
4. **Templates**: Page layouts defining structure (DashboardTemplate, AuthTemplate)
5. **Pages**: Specific instances of templates with real content (Dashboard, Login, Profile)

### Directory Structure

```
src/
├── components/
│   ├── atoms/
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.test.tsx
│   │   │   └── index.ts
│   │   ├── Input/
│   │   └── ...
│   ├── molecules/
│   ├── organisms/
│   └── templates/
├── pages/
│   ├── Dashboard/
│   ├── Login/
│   └── ...
├── contexts/
│   ├── AuthContext.tsx
│   ├── WebSocketContext.tsx
│   └── ...
├── hooks/
│   ├── useAuth.ts
│   ├── useData.ts
│   ├── useWebSocket.ts
│   └── ...
├── services/
│   ├── api/
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   └── interceptors.ts
│   ├── websocket/
│   │   └── client.ts
│   └── cache/
│       └── cache.ts
├── types/
│   ├── auth.ts
│   ├── api.ts
│   └── ...
├── utils/
│   ├── validation.ts
│   ├── formatting.ts
│   └── ...
├── styles/
│   └── globals.css
├── App.tsx
└── main.tsx
```

## Components and Interfaces

### Core Type Definitions

```typescript
// types/auth.ts
interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  createdAt: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  error: string | null;
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

// types/api.ts
interface ApiResponse<T> {
  data: T;
  message: string;
  status: number;
}

interface ApiError {
  message: string;
  code: string;
  field?: string;
}

interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}

// types/cache.ts
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

interface CacheConfig {
  ttl: number; // Time to live in milliseconds
  maxSize: number; // Maximum cache entries
}
```

### Authentication Service

```typescript
// services/api/auth.ts
class AuthService {
  async login(credentials: LoginCredentials): Promise<ApiResponse<User>> {
    // Validate credentials
    // Send POST request to /api/auth/login
    // Store JWT in HTTPOnly cookie (handled by server)
    // Return user data
  }

  async logout(): Promise<void> {
    // Send POST request to /api/auth/logout
    // Clear client-side state
  }

  async refreshToken(): Promise<boolean> {
    // Send POST request to /api/auth/refresh-token
    // Return success status
  }

  async getCurrentUser(): Promise<User | null> {
    // Send GET request to /api/auth/me
    // Return user data or null
  }
}
```

### API Client with Interceptors

```typescript
// services/api/client.ts
import axios, { AxiosInstance, AxiosError } from 'axios';

class ApiClient {
  private client: AxiosInstance;
  private isRefreshing: boolean = false;
  private refreshQueue: Array<() => void> = [];

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 10000,
      withCredentials: true, // Include cookies
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add any request headers
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config;

        // Handle 401 errors
        if (error.response?.status === 401 && !this.isRefreshing) {
          this.isRefreshing = true;

          try {
            await this.refreshToken();
            this.isRefreshing = false;
            this.processRefreshQueue();
            
            // Retry original request
            return this.client(originalRequest);
          } catch (refreshError) {
            this.isRefreshing = false;
            this.clearRefreshQueue();
            // Redirect to login
            throw refreshError;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private async refreshToken(): Promise<void> {
    // Call refresh token endpoint
  }

  private processRefreshQueue(): void {
    this.refreshQueue.forEach(callback => callback());
    this.refreshQueue = [];
  }

  private clearRefreshQueue(): void {
    this.refreshQueue = [];
  }

  async get<T>(url: string, config?: any): Promise<ApiResponse<T>> {
    const response = await this.client.get(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await this.client.post(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await this.client.put(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: any): Promise<ApiResponse<T>> {
    const response = await this.client.delete(url, config);
    return response.data;
  }
}

export const apiClient = new ApiClient(import.meta.env.VITE_API_BASE_URL);
```

### Cache Layer

```typescript
// services/cache/cache.ts
class CacheManager<T = any> {
  private cache: Map<string, CacheEntry<T>>;
  private config: CacheConfig;

  constructor(config: CacheConfig = { ttl: 300000, maxSize: 100 }) {
    this.cache = new Map();
    this.config = config;
  }

  set(key: string, data: T): void {
    // Check cache size limit
    if (this.cache.size >= this.config.maxSize) {
      this.evictOldest();
    }

    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.config.ttl,
    };

    this.cache.set(key, entry);
  }

  get(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    // Check if expired
    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  invalidate(key: string): void {
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  private evictOldest(): void {
    let oldestKey: string | null = null;
    let oldestTime = Infinity;

    for (const [key, entry] of this.cache.entries()) {
      if (entry.timestamp < oldestTime) {
        oldestTime = entry.timestamp;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.cache.delete(oldestKey);
    }
  }
}

export const dataCache = new CacheManager();
```

### Auth Context

```typescript
// contexts/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AuthContextValue {
  state: AuthState;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    // Check authentication on mount
    checkAuth();
  }, []);

  const checkAuth = async (): Promise<void> => {
    try {
      const user = await authService.getCurrentUser();
      setState({
        isAuthenticated: !!user,
        user,
        loading: false,
        error: null,
      });
    } catch (error) {
      setState({
        isAuthenticated: false,
        user: null,
        loading: false,
        error: null,
      });
    }
  };

  const login = async (credentials: LoginCredentials): Promise<void> => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const response = await authService.login(credentials);
      setState({
        isAuthenticated: true,
        user: response.data,
        loading: false,
        error: null,
      });
    } catch (error) {
      setState({
        isAuthenticated: false,
        user: null,
        loading: false,
        error: error.message,
      });
      throw error;
    }
  };

  const logout = async (): Promise<void> => {
    await authService.logout();
    setState({
      isAuthenticated: false,
      user: null,
      loading: false,
      error: null,
    });
  };

  const refreshUser = async (): Promise<void> => {
    await checkAuth();
  };

  return (
    <AuthContext.Provider value={{ state, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### Data Fetching Hook

```typescript
// hooks/useData.ts
import { useState, useEffect, useCallback } from 'react';

interface UseDataOptions {
  cacheKey?: string;
  cacheTTL?: number;
  refetchInterval?: number;
  enabled?: boolean;
}

interface UseDataResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  mutate: (newData: T) => void;
}

export function useData<T>(
  fetcher: () => Promise<T>,
  options: UseDataOptions = {}
): UseDataResult<T> {
  const {
    cacheKey,
    cacheTTL = 300000,
    refetchInterval,
    enabled = true,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async (useCache: boolean = true): Promise<void> => {
    // Check cache first
    if (useCache && cacheKey) {
      const cached = dataCache.get(cacheKey);
      if (cached) {
        setData(cached);
        setLoading(false);
        // Fetch fresh data in background
        fetchFreshData();
        return;
      }
    }

    await fetchFreshData();
  }, [fetcher, cacheKey]);

  const fetchFreshData = async (): Promise<void> => {
    try {
      setLoading(true);
      const result = await fetcher();
      setData(result);
      setError(null);

      // Update cache
      if (cacheKey) {
        dataCache.set(cacheKey, result);
      }
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  const refetch = useCallback(async (): Promise<void> => {
    await fetchData(false);
  }, [fetchData]);

  const mutate = useCallback((newData: T): void => {
    setData(newData);
    if (cacheKey) {
      dataCache.set(cacheKey, newData);
    }
  }, [cacheKey]);

  useEffect(() => {
    if (enabled) {
      fetchData();
    }
  }, [enabled, fetchData]);

  useEffect(() => {
    if (refetchInterval && enabled) {
      const interval = setInterval(() => {
        fetchData(false);
      }, refetchInterval);

      return () => clearInterval(interval);
    }
  }, [refetchInterval, enabled, fetchData]);

  return { data, loading, error, refetch, mutate };
}
```

### WebSocket Provider

```typescript
// contexts/WebSocketContext.tsx
import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';

interface WebSocketContextValue {
  connected: boolean;
  subscribe: (channel: string, callback: (data: any) => void) => () => void;
  send: (channel: string, data: any) => void;
}

const WebSocketContext = createContext<WebSocketContextValue | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode; url: string }> = ({ 
  children, 
  url 
}) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [subscriptions, setSubscriptions] = useState<Map<string, Set<(data: any) => void>>>(
    new Map()
  );
  const [reconnectAttempts, setReconnectAttempts] = useState<number>(0);
  const [shouldReconnect, setShouldReconnect] = useState<boolean>(true);

  const connect = useCallback((): void => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setConnected(true);
      setReconnectAttempts(0);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const { channel, data } = message;

        // Dispatch to subscribers
        const callbacks = subscriptions.get(channel);
        if (callbacks) {
          callbacks.forEach(callback => callback(data));
        }
      } catch (error) {
        console.error('WebSocket message parse error:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      setConnected(false);
      setSocket(null);

      // Attempt reconnection with exponential backoff
      if (shouldReconnect && reconnectAttempts < 3) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
        setTimeout(() => {
          setReconnectAttempts(prev => prev + 1);
          connect();
        }, delay);
      } else if (reconnectAttempts >= 3) {
        // Fall back to polling
        console.warn('WebSocket reconnection failed, falling back to polling');
      }
    };

    setSocket(ws);
  }, [url, reconnectAttempts, shouldReconnect, subscriptions]);

  useEffect(() => {
    connect();

    return () => {
      setShouldReconnect(false);
      if (socket) {
        socket.close();
      }
    };
  }, []);

  const subscribe = useCallback((
    channel: string, 
    callback: (data: any) => void
  ): (() => void) => {
    setSubscriptions(prev => {
      const newSubs = new Map(prev);
      const channelSubs = newSubs.get(channel) || new Set();
      channelSubs.add(callback);
      newSubs.set(channel, channelSubs);
      return newSubs;
    });

    // Return unsubscribe function
    return () => {
      setSubscriptions(prev => {
        const newSubs = new Map(prev);
        const channelSubs = newSubs.get(channel);
        if (channelSubs) {
          channelSubs.delete(callback);
          if (channelSubs.size === 0) {
            newSubs.delete(channel);
          } else {
            newSubs.set(channel, channelSubs);
          }
        }
        return newSubs;
      });
    };
  }, []);

  const send = useCallback((channel: string, data: any): void => {
    if (socket && connected) {
      socket.send(JSON.stringify({ channel, data }));
    }
  }, [socket, connected]);

  return (
    <WebSocketContext.Provider value={{ connected, subscribe, send }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextValue => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
};
```

### Route Guard Component

```typescript
// components/organisms/RouteGuard/RouteGuard.tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';

interface RouteGuardProps {
  children: React.ReactNode;
}

export const RouteGuard: React.FC<RouteGuardProps> = ({ children }) => {
  const { state } = useAuth();
  const location = useLocation();

  if (state.loading) {
    return <div>Loading...</div>;
  }

  if (!state.isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
```

### Form Component with Validation

```typescript
// components/organisms/LoginForm/LoginForm.tsx
import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '../../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginForm: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData): Promise<void> => {
    try {
      await login(data);
      navigate('/dashboard');
    } catch (error) {
      setError('root', {
        message: 'Invalid credentials. Please try again.',
      });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email
        </label>
        <input
          {...register('email')}
          type="email"
          id="email"
          className="mt-1 block w-full rounded-md border p-2"
          aria-invalid={errors.email ? 'true' : 'false'}
        />
        {errors.email && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors.email.message}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium">
          Password
        </label>
        <input
          {...register('password')}
          type="password"
          id="password"
          className="mt-1 block w-full rounded-md border p-2"
          aria-invalid={errors.password ? 'true' : 'false'}
        />
        {errors.password && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors.password.message}
          </p>
        )}
      </div>

      {errors.root && (
        <p className="text-sm text-red-600" role="alert">
          {errors.root.message}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Logging in...' : 'Log In'}
      </button>
    </form>
  );
};
```

## Data Models

### User Model

```typescript
interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  avatar?: string;
  createdAt: string;
  updatedAt: string;
}
```

### Authentication Models

```typescript
interface LoginCredentials {
  email: string;
  password: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  error: string | null;
}

interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}
```

### API Models

```typescript
interface ApiResponse<T> {
  data: T;
  message: string;
  status: number;
  timestamp: string;
}

interface ApiError {
  message: string;
  code: string;
  field?: string;
  details?: Record<string, any>;
}

interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}
```

### WebSocket Models

```typescript
interface WebSocketMessage {
  channel: string;
  data: any;
  timestamp: string;
}

interface WebSocketSubscription {
  channel: string;
  callback: (data: any) => void;
}
```

### Form Models

```typescript
interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'number' | 'select' | 'textarea';
  placeholder?: string;
  required?: boolean;
  validation?: z.ZodSchema;
}

interface FormState<T> {
  values: T;
  errors: Record<keyof T, string>;
  touched: Record<keyof T, boolean>;
  isSubmitting: boolean;
  isValid: boolean;
}
```


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property Reflection

After analyzing all acceptance criteria, I identified the following redundancies:
- Properties 6.4 and 7.4 both test lazy loading for route components - these will be combined
- Properties 6.3 and 13.2 both test design token usage - these will be combined
- Several properties test similar caching behaviors (2.1, 2.2, 2.4) - these can be consolidated into comprehensive cache behavior properties

### Authentication Properties

**Property 1: Valid credentials trigger API request**
*For any* valid login credentials (email and password meeting format requirements), when submitted through the Auth_Service, an API request should be sent to the authentication endpoint with the correct payload structure.
**Validates: Requirements 1.1**

**Property 2: Successful authentication updates context state**
*For any* successful authentication response containing user data, the Auth_Context should update isAuthenticated to true and store the complete user profile in state.
**Validates: Requirements 1.3**

**Property 3: Successful authentication redirects to dashboard**
*For any* successful login completion, the Frontend_System should navigate to the dashboard route.
**Validates: Requirements 1.4**

**Property 4: 401 responses trigger token refresh**
*For any* API request that returns a 401 status code, the Token_Interceptor should attempt to refresh the authentication token before failing the request.
**Validates: Requirements 1.5**

**Property 5: Successful token refresh retries original request**
*For any* API request that failed with 401 and successfully refreshed the token, the original request should be retried with the same parameters and headers.
**Validates: Requirements 1.6**

**Property 6: Failed token refresh clears authentication**
*For any* token refresh attempt that fails, the Auth_Context should clear all authentication state (set isAuthenticated to false, clear user data) and redirect to the login page.
**Validates: Requirements 1.7**

### Data Fetching and Caching Properties

**Property 7: Cache-first data fetching**
*For any* data request with a cache key, the Data_Hook should check the Cache_Layer first and return cached data immediately if it exists and is not expired.
**Validates: Requirements 2.1, 2.2**

**Property 8: Stale-while-revalidate pattern**
*For any* data request that returns cached data, the Data_Hook should fetch fresh data in the background and update the component when the fresh data arrives.
**Validates: Requirements 2.3**

**Property 9: Cache miss triggers fetch and store**
*For any* data request where cached data does not exist or is expired, the Data_Hook should fetch data from the API and store the result in the Cache_Layer with the appropriate TTL.
**Validates: Requirements 2.4**

**Property 10: Optimistic UI updates**
*For any* data mutation action, the Frontend_System should update the UI immediately with the expected result before receiving the API response.
**Validates: Requirements 2.5**

**Property 11: Failed mutations rollback UI state**
*For any* optimistic update where the API request fails, the Frontend_System should revert the UI to the state before the optimistic update and display an error message.
**Validates: Requirements 2.6**

**Property 12: Exponential backoff retry logic**
*For any* failed data fetch request, the Data_Hook should retry the request up to 3 times with exponentially increasing delays (e.g., 1s, 2s, 4s) before giving up.
**Validates: Requirements 2.7**

### Form Management Properties

**Property 13: Form fields bound to validation schema**
*For any* form rendered with a validation schema, all input fields should be bound to the schema and validation rules should be applied.
**Validates: Requirements 3.1**

**Property 14: Real-time field validation**
*For any* input change in a form field, the Form_Manager should validate the new value against the schema and display validation feedback immediately.
**Validates: Requirements 3.2**

**Property 15: Invalid forms prevent submission**
*For any* form submission attempt where validation fails, the Form_Manager should prevent the submission and highlight all fields with validation errors.
**Validates: Requirements 3.3**

**Property 16: Valid forms trigger async validation**
*For any* form with valid client-side data and async validation configured, the Form_Manager should perform async validation before final submission.
**Validates: Requirements 3.4**

**Property 17: Successful validation submits data**
*For any* form where all validation (sync and async) passes, the Form_Manager should submit the form data to the API_Gateway.
**Validates: Requirements 3.5**

**Property 18: Server errors map to form fields**
*For any* form submission that fails with field-specific server errors, the Form_Manager should display each error message next to the corresponding form field.
**Validates: Requirements 3.6**

### Real-time Updates Properties

**Property 19: Component subscriptions are registered**
*For any* component that subscribes to a WebSocket channel, the WebSocket_Provider should register the subscription and maintain it until unsubscribed.
**Validates: Requirements 4.2**

**Property 20: Messages dispatch to all subscribers**
*For any* WebSocket message received on a channel, the WebSocket_Provider should dispatch the message to all components subscribed to that channel.
**Validates: Requirements 4.3**

**Property 21: Connection failures trigger reconnection**
*For any* WebSocket connection failure, the WebSocket_Provider should attempt to reconnect with exponentially increasing delays between attempts.
**Validates: Requirements 4.4**

**Property 22: Cleanup closes WebSocket connection**
*For any* application unmount or user logout event, the WebSocket_Provider should close the WebSocket connection gracefully.
**Validates: Requirements 4.6**

### Responsive Design Properties

**Property 23: Mobile viewport renders mobile layouts**
*For any* UI_Component rendered at viewport width below 640px, the component should apply mobile-optimized layout classes and styles.
**Validates: Requirements 5.2**

**Property 24: Tablet viewport renders tablet layouts**
*For any* UI_Component rendered at viewport width between 640px and 768px, the component should apply tablet-optimized layout classes and styles.
**Validates: Requirements 5.3**

**Property 25: Desktop viewport renders desktop layouts**
*For any* UI_Component rendered at viewport width above 768px, the component should apply desktop-optimized layout classes and styles.
**Validates: Requirements 5.4**

**Property 26: Dynamic viewport changes update layout**
*For any* viewport size change, UI_Components should adapt their layout without requiring a page reload.
**Validates: Requirements 5.5**

**Property 27: Touch targets meet minimum size**
*For any* interactive UI element on mobile devices, the touch target should be at least 44x44 pixels to meet accessibility standards.
**Validates: Requirements 5.6**

### Component Architecture Properties

**Property 28: Components use design system tokens**
*For any* UI_Component that applies styling, the component should use design system tokens (CSS variables or Tailwind classes) for spacing, colors, and typography rather than hardcoded values.
**Validates: Requirements 6.3, 13.2**

**Property 29: Route components are lazy loaded**
*For any* route-level component, the component should be dynamically imported using React.lazy() to enable code splitting and reduce initial bundle size.
**Validates: Requirements 6.4, 7.4**

### Routing and Navigation Properties

**Property 30: Unauthenticated access redirects to login**
*For any* protected route accessed without valid authentication, the Route_Guard should redirect to the login page and preserve the intended destination.
**Validates: Requirements 7.2**

**Property 31: Authenticated access renders protected content**
*For any* protected route accessed with valid authentication, the Route_Guard should render the requested component without redirection.
**Validates: Requirements 7.3**

**Property 32: Back navigation preserves scroll position**
*For any* navigation back to a previously visited route, the Frontend_System should restore the scroll position to where it was when the user left that route.
**Validates: Requirements 7.5**

### Performance Properties

**Property 33: Images below fold are lazy loaded**
*For any* image element that is not in the initial viewport, the image should not load until it is about to enter the viewport (lazy loading).
**Validates: Requirements 8.3**

**Property 34: Responsive images match viewport**
*For any* image rendered at different viewport sizes, the Frontend_System should serve appropriately sized image assets based on the current viewport width.
**Validates: Requirements 8.4**

### Accessibility Properties

**Property 35: Interactive elements are keyboard navigable**
*For any* interactive UI_Component (buttons, links, form inputs), the element should be reachable via keyboard navigation and display a visible focus indicator.
**Validates: Requirements 9.2**

**Property 36: Color-independent information**
*For any* UI_Component that conveys information through color, the component should also provide the same information through text, icons, or patterns.
**Validates: Requirements 9.3**

**Property 37: Text meets contrast requirements**
*For any* text content, the color contrast ratio should be at least 4.5:1 for normal text and 3:1 for large text (18pt+ or 14pt+ bold).
**Validates: Requirements 9.4**

**Property 38: Icons have aria-labels**
*For any* icon used in a UI_Component, the icon should have an aria-label or aria-labelledby attribute providing a text description for screen readers.
**Validates: Requirements 9.5**

**Property 39: Form errors announced to screen readers**
*For any* form validation error, the Form_Manager should use aria-live regions to announce the error to screen readers.
**Validates: Requirements 9.6**

**Property 40: Semantic HTML structure**
*For any* page, the Frontend_System should use proper heading hierarchy (h1-h6) and ARIA landmark regions (main, nav, aside, footer) for screen reader navigation.
**Validates: Requirements 9.7**

### Error Handling Properties

**Property 41: API errors display user-friendly messages**
*For any* API request that fails, the Frontend_System should display a user-friendly error message (not raw error codes or stack traces).
**Validates: Requirements 10.1**

**Property 42: Error boundaries catch unexpected errors**
*For any* unexpected error thrown during rendering, the Frontend_System should catch it with an Error Boundary and display a fallback UI instead of crashing.
**Validates: Requirements 10.2**

**Property 43: Network errors show retry option**
*For any* network error (timeout, connection refused, etc.), the Frontend_System should display a network-specific error message with a retry button.
**Validates: Requirements 10.3**

**Property 44: Server validation errors map to fields**
*For any* form submission that fails with server-side validation errors, the Form_Manager should display each error next to the corresponding form field.
**Validates: Requirements 10.4**

**Property 45: Errors are logged to monitoring service**
*For any* error that occurs (API errors, unexpected errors, network errors), the Frontend_System should log the error details to a monitoring service.
**Validates: Requirements 10.5**

**Property 46: User input preserved on errors**
*For any* error that occurs during form submission or data entry, the Frontend_System should preserve the user's input data so it is not lost.
**Validates: Requirements 10.6**

### Type Safety Properties

**Property 47: API responses validated against types**
*For any* API response received, the Frontend_System should validate the response structure against the expected TypeScript interface before using the data.
**Validates: Requirements 11.3**

### State Management Properties

**Property 48: State updates are immutable**
*For any* state update operation, the Frontend_System should create a new state object rather than mutating the existing state object.
**Validates: Requirements 15.2**

**Property 49: User preferences persist to localStorage**
*For any* user preference change (theme, language, layout settings), the Frontend_System should save the preference to localStorage and restore it on subsequent visits.
**Validates: Requirements 15.5**

## Error Handling

### Error Boundary Implementation

The application implements a global Error Boundary component that catches React rendering errors and displays a fallback UI:

```typescript
// components/organisms/ErrorBoundary/ErrorBoundary.tsx
import React, { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log to monitoring service
    console.error('Error caught by boundary:', error, errorInfo);
    // Send to error tracking service (e.g., Sentry)
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex min-h-screen items-center justify-center p-4">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Something went wrong</h1>
            <p className="mt-2 text-gray-600">
              We're sorry for the inconvenience. Please try refreshing the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-white"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### Error Types and Handling Strategies

1. **API Errors**: Caught by axios interceptors, displayed with user-friendly messages
2. **Network Errors**: Detected by checking error type, show retry option
3. **Validation Errors**: Handled by form manager, displayed inline with fields
4. **Rendering Errors**: Caught by Error Boundary, show fallback UI
5. **Authentication Errors**: Handled by auth interceptor, trigger logout or refresh

### Error Logging

All errors are logged to a monitoring service with the following information:
- Error message and stack trace
- User context (ID, role, authentication status)
- Request context (URL, method, payload)
- Browser and device information
- Timestamp and session ID

## Testing Strategy

### Dual Testing Approach

The application uses both unit tests and property-based tests for comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
- Component rendering with specific props
- User interactions (clicks, form submissions)
- Edge cases (empty states, error states)
- Integration between components

**Property-Based Tests**: Verify universal properties across all inputs
- Authentication flows with random credentials
- Data fetching with various cache states
- Form validation with generated input data
- Responsive behavior across viewport ranges
- Accessibility requirements across all components

### Testing Tools and Configuration

**Unit Testing**:
- Framework: Vitest
- Component Testing: React Testing Library
- Minimum 100 iterations per property test
- Coverage target: 80% overall

**End-to-End Testing**:
- Framework: Playwright
- Critical user flows: Login, Dashboard navigation, Form submissions
- Cross-browser testing: Chrome, Firefox, Safari

**Property-Based Testing**:
- Library: fast-check (for TypeScript/JavaScript)
- Configuration: Minimum 100 iterations per property
- Each test tagged with: **Feature: frontend-architecture, Property {number}: {property_text}**

### Test Organization

```
src/
├── components/
│   ├── atoms/
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.test.tsx          # Unit tests
│   │   │   └── Button.properties.test.tsx # Property tests
├── hooks/
│   ├── useData.ts
│   ├── useData.test.ts
│   └── useData.properties.test.ts
tests/
├── e2e/
│   ├── auth.spec.ts
│   ├── dashboard.spec.ts
│   └── forms.spec.ts
└── properties/
    ├── auth.properties.test.ts
    ├── data-fetching.properties.test.ts
    └── forms.properties.test.ts
```

### Example Property Test

```typescript
// tests/properties/auth.properties.test.ts
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';

describe('Feature: frontend-architecture, Property 2: Successful authentication updates context state', () => {
  it('should update auth context state for any successful auth response', () => {
    fc.assert(
      fc.property(
        fc.record({
          id: fc.uuid(),
          email: fc.emailAddress(),
          name: fc.string({ minLength: 1, maxLength: 50 }),
          role: fc.constantFrom('admin', 'user'),
          createdAt: fc.date().map(d => d.toISOString()),
        }),
        (userData) => {
          // Test that auth context updates correctly
          const authContext = new AuthContext();
          authContext.handleLoginSuccess(userData);
          
          expect(authContext.state.isAuthenticated).toBe(true);
          expect(authContext.state.user).toEqual(userData);
          expect(authContext.state.error).toBeNull();
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

### CI/CD Integration

All tests run automatically in the CI/CD pipeline:
1. Lint and type check
2. Unit tests with coverage report
3. Property-based tests (100 iterations each)
4. E2E tests on multiple browsers
5. Build verification
6. Bundle size check

The pipeline blocks merges if:
- Any test fails
- Coverage drops below 80%
- TypeScript errors exist
- Bundle size exceeds 200KB (gzipped)

## Visual Design System

### Color Palette

```typescript
// Semantic colors defined in Tailwind config
const colors = {
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    500: '#3b82f6',  // Main primary
    600: '#2563eb',
    700: '#1d4ed8',
  },
  secondary: {
    500: '#6b7280',
    600: '#4b5563',
  },
  success: {
    500: '#10b981',
    600: '#059669',
  },
  error: {
    500: '#ef4444',
    600: '#dc2626',
  },
  warning: {
    500: '#f59e0b',
    600: '#d97706',
  },
  info: {
    500: '#06b6d4',
    600: '#0891b2',
  },
};
```

### Spacing System

Based on Tailwind CSS scale (4px base unit):

- **XS (4px)**: `gap-1`, `p-1`, `m-1` - Tight spacing within components
- **SM (8px)**: `gap-2`, `p-2`, `m-2` - Small component padding
- **MD (16px)**: `gap-4`, `p-4`, `m-4` - Standard component spacing (default)
- **LG (24px)**: `gap-6`, `p-6`, `m-6` - Comfortable spacing between elements
- **XL (32px)**: `gap-8`, `p-8`, `m-8` - Section dividers
- **XXL (48px)**: `gap-12`, `p-12`, `m-12` - Page margins and major sections

### Typography Scale

```typescript
const typography = {
  // Font families
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
    mono: ['Fira Code', 'monospace'],
  },
  
  // Font sizes
  fontSize: {
    xs: ['0.75rem', { lineHeight: '1rem' }],      // 12px
    sm: ['0.875rem', { lineHeight: '1.25rem' }],  // 14px
    base: ['1rem', { lineHeight: '1.5rem' }],     // 16px
    lg: ['1.125rem', { lineHeight: '1.75rem' }],  // 18px
    xl: ['1.25rem', { lineHeight: '1.75rem' }],   // 20px
    '2xl': ['1.5rem', { lineHeight: '2rem' }],    // 24px
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }],   // 36px
  },
  
  // Font weights
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
};
```

### Component Styling Guidelines

**Buttons**:
- Primary: `bg-primary-600 hover:bg-primary-700 text-white`
- Secondary: `bg-secondary-100 hover:bg-secondary-200 text-secondary-900`
- Padding: `px-4 py-2` (MD spacing)
- Border radius: `rounded-md` (6px)

**Cards**:
- Background: `bg-white`
- Border: `border border-gray-200`
- Shadow: `shadow-sm` or `shadow-md`
- Padding: `p-6` (LG spacing)
- Border radius: `rounded-lg` (8px)

**Form Inputs**:
- Border: `border border-gray-300 focus:border-primary-500`
- Padding: `px-3 py-2`
- Border radius: `rounded-md`
- Focus ring: `focus:ring-2 focus:ring-primary-500 focus:ring-offset-2`

### Responsive Breakpoints

```typescript
const breakpoints = {
  sm: '640px',   // Mobile landscape, small tablets
  md: '768px',   // Tablets
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large desktop
  '2xl': '1536px', // Extra large desktop
};
```

### Accessibility Guidelines

- Minimum touch target: 44x44px on mobile
- Color contrast: 4.5:1 for normal text, 3:1 for large text
- Focus indicators: 2px solid ring with offset
- ARIA labels for all interactive elements
- Semantic HTML with proper heading hierarchy
- Keyboard navigation support for all interactive elements

## Deployment and Build Configuration

### Environment Variables

```typescript
// .env.development
VITE_API_BASE_URL=http://localhost:3000/api
VITE_WS_URL=ws://localhost:3000/ws
VITE_ENV=development

// .env.production
VITE_API_BASE_URL=https://api.aiforbharat.org/api
VITE_WS_URL=wss://api.aiforbharat.org/ws
VITE_ENV=production
```

### Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    react(),
    visualizer({ open: true, gzipSize: true }),
  ],
  build: {
    target: 'es2020',
    minify: 'terser',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'form-vendor': ['react-hook-form', 'zod'],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
  },
});
```

### Build Optimization Strategies

1. **Code Splitting**: Route-based splitting using React.lazy()
2. **Tree Shaking**: Automatic with Vite for ES modules
3. **Minification**: Terser for production builds
4. **Compression**: Gzip and Brotli compression
5. **Asset Optimization**: Image optimization and lazy loading
6. **Bundle Analysis**: Visualizer plugin for bundle size monitoring

### Performance Targets

- Initial bundle size: < 200KB (gzipped)
- Time to Interactive (TTI): < 3s on 3G
- First Contentful Paint (FCP): < 1.5s
- Lighthouse Performance Score: > 90
- Lighthouse Accessibility Score: > 95
