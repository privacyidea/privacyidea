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
import { Component, effect, inject, signal } from "@angular/core";
import { MatProgressBar } from "@angular/material/progress-bar";
import { RouterOutlet } from "@angular/router";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { LoadingService, LoadingServiceInterface } from "../../services/loading/loading-service";
import { MatDrawer, MatDrawerContainer, MatDrawerContent } from "@angular/material/sidenav";
import { NavigationComponent } from "./navigation/navigation.component";
import { OverflowService, OverflowServiceInterface } from "../../services/overflow/overflow.service";
import { ContentService, ContentServiceInterface } from "../../services/content/content.service";

@Component({
  selector: "layout",
  templateUrl: "layout.component.html",
  standalone: true,
  imports: [RouterOutlet, MatProgressBar, MatDrawer, MatDrawerContainer, MatDrawerContent, NavigationComponent],
  styleUrl: "./layout.component.scss"
})
export class LayoutComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly loadingService: LoadingServiceInterface = inject(LoadingService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  showProgressBar = signal(false);
  loadingUrls = signal<{ key: string; url: string }[]>([]);
  isTokenDrawerOverflowing = signal(false);

  constructor() {
    effect(() => {
      this.contentService.routeUrl();
      this.updateOverflowState();
    });
  }

  ngAfterViewInit() {
    window.addEventListener("resize", this.updateOverflowState.bind(this));
    this.updateOverflowState();
  }

  updateOverflowState() {
    setTimeout(() => {
      this.isTokenDrawerOverflowing.set(
        this.overflowService.isHeightOverflowing({
          selector: ".token-layout",
          thresholdSelector: ".drawer"
        })
      );
    }, 400);
  }

  ngOnInit(): void {
    this.loadingService.addListener("layout", () => {
      this.showProgressBar.set(this.loadingService.isLoading());
      this.loadingUrls.set(this.loadingService.getLoadingUrls());
    });
  }

  ngOnDestroy(): void {
    this.loadingService.removeListener("layout");
    window.removeEventListener("resize", this.updateOverflowState);
  }
}
