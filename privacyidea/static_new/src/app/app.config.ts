import { APP_BASE_HREF } from "@angular/common";
import { provideHttpClient, withInterceptors } from "@angular/common/http";
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideExperimentalZonelessChangeDetection
} from "@angular/core";
import { provideAnimationsAsync } from "@angular/platform-browser/animations/async";
import { provideRouter } from "@angular/router";
import { routes } from "./app.routes";
import { loadingInterceptor } from "./interceptor/loading/loading.interceptor";
import { AuthService } from "./services/auth/auth.service";
import { ThemeService } from "./services/theme/theme.service";

export const appConfig: ApplicationConfig = {
  providers: [
    provideExperimentalZonelessChangeDetection(),
    provideRouter(routes),
    provideAnimationsAsync(),
    { provide: APP_BASE_HREF, useValue: "/app/v2/" },
    AuthService,
    provideHttpClient(withInterceptors([loadingInterceptor])),
    provideAppInitializer(() => {
      const themeService = inject(ThemeService);
      themeService.initializeTheme();
    })
  ]
};
