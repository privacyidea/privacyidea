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
import { Component, effect, inject, Renderer2, signal, DOCUMENT } from "@angular/core";

import { MatProgressBar } from "@angular/material/progress-bar";
import { RouterOutlet } from "@angular/router";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { LoadingService, LoadingServiceInterface } from "../../services/loading/loading-service";
import { MatDrawer, MatDrawerContainer, MatDrawerContent } from "@angular/material/sidenav";
import { NavigationComponent } from "./navigation/navigation.component";
import { ContentService, ContentServiceInterface } from "../../services/content/content.service";
import { NavigationSelfServiceComponent } from "./navigation-self-service/navigation-self-service.component";
import { NavigationSelfServiceWizardComponent } from "./navigation-self-service/navigation-self-service.wizard.component";

@Component({
  selector: "layout",
  templateUrl: "layout.component.html",
  standalone: true,
  imports: [RouterOutlet, MatProgressBar, MatDrawer, MatDrawerContainer, MatDrawerContent, NavigationComponent, NavigationSelfServiceComponent, NavigationSelfServiceWizardComponent],
  styleUrl: "./layout.component.scss"
})
export class LayoutComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly loadingService: LoadingServiceInterface = inject(LoadingService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly renderer = inject(Renderer2);
  private readonly document = inject(DOCUMENT);
  showProgressBar = signal(false);
  loadingUrls = signal<{ key: string; url: string }[]>([]);

  constructor() {
    effect(() => {
      this.contentService.routeUrl();
      this.updateBodyClasses();
    });
  }

  updateBodyClasses() {
    if (this.authService.role() === "admin") {
      this.renderer.addClass(this.document.body, "admin-layout");
      this.renderer.removeClass(this.document.body, "self-service-layout");
    } else {
      this.renderer.addClass(this.document.body, "self-service-layout");
      this.renderer.removeClass(this.document.body, "admin-layout");
    }
  }

  ngOnInit(): void {
    this.loadingService.addListener("layout", () => {
      this.showProgressBar.set(this.loadingService.isLoading());
      this.loadingUrls.set(this.loadingService.getLoadingUrls());
    });
  }

  ngOnDestroy(): void {
    this.renderer.removeClass(this.document.body, "admin-layout");
    this.renderer.removeClass(this.document.body, "self-service-layout");
    this.loadingService.removeListener("layout");
  }
}
