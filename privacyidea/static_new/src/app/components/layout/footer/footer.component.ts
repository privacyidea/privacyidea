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
import { Component, inject, OnInit, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatProgressBar } from "@angular/material/progress-bar";
import { LoadingService, LoadingServiceInterface } from "../../../services/loading/loading-service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";

@Component({
  selector: "app-footer",
  standalone: true,
  imports: [MatIconModule, MatButtonModule, MatProgressBar],
  templateUrl: "./footer.component.html",
  styleUrl: "./footer.component.scss"
})
export class FooterComponent implements OnInit {
  private readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  private readonly loadingService: LoadingServiceInterface = inject(LoadingService);

  version!: string;
  showProgressBar = signal(false);
  loadingUrls = signal<{ key: string; url: string }[]>([]);

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
    this.loadingService.addListener("footer", () => {
      this.showProgressBar.set(this.loadingService.isLoading());
      this.loadingUrls.set(this.loadingService.getLoadingUrls());
    });
  }

  ngOnDestroy(): void {
    this.loadingService.removeListener("footer");
  }
}
