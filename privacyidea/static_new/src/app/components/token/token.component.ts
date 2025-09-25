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
import { MatFabButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatDrawer, MatDrawerContainer, MatSidenavModule } from "@angular/material/sidenav";
import { RouterOutlet } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../services/content/content.service";
import { OverflowService, OverflowServiceInterface } from "../../services/overflow/overflow.service";
import { ContainerDetailsComponent } from "./container-details/container-details.component";
import { ContainerTableComponent } from "./container-table/container-table.component";
import { TokenCardComponent } from "./token-card/token-card.component";
import { TokenDetailsComponent } from "./token-details/token-details.component";
import { TokenTableComponent } from "./token-table/token-table.component";

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
    TokenCardComponent,
    MatDrawerContainer,
    MatDrawer,
    MatSidenavModule,
    MatIcon,
    MatFabButton,
    RouterOutlet
  ],
  templateUrl: "./token.component.html",
  styleUrl: "./token.component.scss"
})
export class TokenComponent {
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
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
}
