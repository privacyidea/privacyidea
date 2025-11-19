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
import { CommonModule } from "@angular/common";
import { Component, effect, inject, signal, ViewChild } from "@angular/core";
import { MatDrawer, MatDrawerContainer, MatSidenavModule } from "@angular/material/sidenav";
import { Router, RouterOutlet } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../services/content/content.service";
import { OverflowService, OverflowServiceInterface } from "../../services/overflow/overflow.service";
import { ContainerDetailsComponent } from "./container-details/container-details.component";
import { ContainerTableComponent } from "./container-table/container-table.component";
import { TokenDetailsComponent } from "./token-details/token-details.component";
import { TokenTableComponent } from "./token-table/token-table.component";
import { ROUTE_PATHS } from "../../route_paths";
import { MatExpansionModule } from "@angular/material/expansion";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { VersioningService, VersioningServiceInterface } from "../../services/version/version.service";
import { SessionTimerService, SessionTimerServiceInterface } from "../../services/session-timer/session-timer.service";
import { LocalService, LocalServiceInterface } from "../../services/local/local.service";
import { NotificationService, NotificationServiceInterface } from "../../services/notification/notification.service";
import { MatDividerModule } from "@angular/material/divider";
import { NavigationComponent } from "./navigation/navigation.component";

export type TokenTypeOption =
  | "hotp"
  | "totp"
  | "spass"
  | "motp"
  | "sshkey"
  | "yubikey"
  | "remote"
  | "yubico"
  | "radius"
  | "sms"
  | "4eyes"
  | "applspec"
  | "certificate"
  | "daypassword"
  | "email"
  | "indexedsecret"
  | "paper"
  | "push"
  | "question"
  | "registration"
  | "tan"
  | "tiqr"
  | "u2f"
  | "vasco"
  | "webauthn"
  | "passkey";

@Component({
  selector: "app-token",
  standalone: true,
  imports: [
    CommonModule,
    MatDrawerContainer,
    MatDrawer,
    MatSidenavModule,
    RouterOutlet,
    MatExpansionModule,
    MatDividerModule,
    NavigationComponent
  ],
  templateUrl: "./token.component.html",
  styleUrl: "./token.component.scss"
})
export class TokenComponent {
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);
  protected readonly localService: LocalServiceInterface = inject(LocalService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly router: Router = inject(Router);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  tokenTypeOptions = signal([]);
  isTokenDrawerOverflowing = signal(false);
  @ViewChild("tokenDetailsComponent")
  tokenDetailsComponent!: TokenDetailsComponent;
  @ViewChild("containerDetailsComponent")
  containerDetailsComponent!: ContainerDetailsComponent;
  @ViewChild("tokenTableComponent") tokenTableComponent!: TokenTableComponent;
  @ViewChild("containerTableComponent")
  containerTableComponent!: ContainerTableComponent;
  @ViewChild("drawer") drawer!: MatDrawer;

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

  ngOnDestroy() {
    window.removeEventListener("resize", this.updateOverflowState);
  }

  i = 42;
}
