import { NgClass } from "@angular/common";
import { Component, inject, linkedSignal } from "@angular/core";
import { MatCard, MatCardContent } from "@angular/material/card";
import { MatIcon } from "@angular/material/icon";
import { MatTabChangeEvent, MatTabsModule } from "@angular/material/tabs";

import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { OverflowService, OverflowServiceInterface } from "../../../services/overflow/overflow.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";

import { Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../app.routes";
import { ContainerTabComponent } from "./container-tab/container-tab.component";
import { TokenTabComponent } from "./token-tab/token-tab.component";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";

@Component({
  selector: "app-token-card",
  standalone: true,
  imports: [MatCardContent, MatTabsModule, MatCard, MatIcon, TokenTabComponent, ContainerTabComponent, NgClass],
  templateUrl: "./token-card.component.html",
  styleUrls: ["./token-card.component.scss"]
})
export class TokenCardComponent {
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private router = inject(Router);
  selectedTabIndex = linkedSignal({
    source: this.contentService.routeUrl,
    computation: (routeUrl) => (routeUrl.startsWith(ROUTE_PATHS.TOKENS_CONTAINERS) ? 1 : 0)
  });
  tokenSerial = this.tokenService.tokenSerial;
  containerSerial = this.containerService.containerSerial;
  states = this.containerService.states;
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;

  onTabChange(event: MatTabChangeEvent): void {
    if (this.isProgrammaticTabChange()) {
      this.isProgrammaticTabChange.set(false);
      return;
    }
    if (event.index === 0) {
      this.router.navigateByUrl(ROUTE_PATHS.TOKENS);
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS);
    }
  }

  anyTokenActionAllowed(): boolean {
    const allowed = this.authService.oneActionAllowed(
      ["tokenlist", "getchallenges", "getserial", "machinelist"]);
    return allowed || this.tokenService.enrollmentAllowed();
  }

  anyContainerActionAllowed(): boolean {
    return this.authService.oneActionAllowed(
      ["container_list", "container_create", "container_template_list", "container_template_create"]);
  }

  tokenTabActive = () => this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS) && !this.containerTabActive();
  containerTabActive = () => this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_CONTAINERS);
}
