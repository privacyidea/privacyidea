/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
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
