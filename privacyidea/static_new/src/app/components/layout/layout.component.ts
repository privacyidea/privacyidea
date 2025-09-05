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
import { NgClass } from "@angular/common";
import { Component, inject, signal } from "@angular/core";
import { MatProgressBar } from "@angular/material/progress-bar";
import { RouterOutlet } from "@angular/router";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { LoadingService, LoadingServiceInterface } from "../../services/loading/loading-service";
import { HeaderComponent } from "./header/header.component";
import { HeaderSelfServiceComponent } from "./header/header.self-service.component";

@Component({
  selector: "layout",
  templateUrl: "layout.component.html",
  standalone: true,
  imports: [RouterOutlet, HeaderComponent, HeaderSelfServiceComponent, NgClass, MatProgressBar],
  styleUrl: "./layout.component.scss"
})
export class LayoutComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly loadingService: LoadingServiceInterface = inject(LoadingService);
  showProgressBar = signal(false);
  loadingUrls = signal<{ key: string; url: string }[]>([]);

  ngOnInit(): void {
    this.loadingService.addListener("layout", () => {
      this.showProgressBar.set(this.loadingService.isLoading());
      this.loadingUrls.set(this.loadingService.getLoadingUrls());
    });
  }

  ngOnDestroy(): void {
    this.loadingService.removeListener("layout");
  }
}
