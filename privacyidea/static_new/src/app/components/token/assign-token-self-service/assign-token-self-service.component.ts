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
import { AfterViewInit, Component, ElementRef, inject, OnDestroy, Renderer2, signal, ViewChild } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton } from "@angular/material/button";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../route_paths";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";

@Component({
  selector: "app-attach-token-self-service",
  imports: [MatError, MatFormField, MatLabel, MatInput, FormsModule, MatButton, MatIcon, ScrollToTopDirective],
  templateUrl: "./assign-token-self-service.component.html",
  styleUrl: "./assign-token-self-service.component.scss"
})
export class AssignTokenSelfServiceComponent implements AfterViewInit, OnDestroy {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly renderer: Renderer2 = inject(Renderer2);
  private router = inject(Router);
  tokenSerial = this.tokenService.tokenSerial;
  selectedToken = signal("");
  setPinValue = signal("");
  repeatPinValue = signal("");

  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;

  private observer!: IntersectionObserver;

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) {
      return;
    }

    this.observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
      } else {
        this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
      }
    });

    this.observer.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  assignUserToToken() {
    this.tokenService
      .assignUser({
        tokenSerial: this.selectedToken(),
        username: "",
        realm: "",
        pin: this.setPinValue()
      })
      .subscribe({
        next: () => {
          this.router.navigateByUrl(ROUTE_PATHS.TOKENS_DETAILS + this.selectedToken());
          this.tokenSerial.set(this.selectedToken());
        }
      });
  }
}
