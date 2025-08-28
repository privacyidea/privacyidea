import { CommonModule } from "@angular/common";
import { Component, effect, inject, signal, ViewChild } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatDrawer, MatSidenavModule } from "@angular/material/sidenav";
import { RouterOutlet } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../services/content/content.service";
import { OverflowService, OverflowServiceInterface } from "../../services/overflow/overflow.service";
import { UserService, UserServiceInterface } from "../../services/user/user.service";
import { UserCardComponent } from "./user-card/user-card.component";
import { UserDetailsComponent } from "./user-details/user-details.component";
import { UserTableComponent } from "./user-table/user-table.component";

@Component({
  selector: "app-user",
  standalone: true,
  imports: [CommonModule, UserCardComponent, MatSidenavModule, RouterOutlet, MatIcon, MatButtonModule],
  templateUrl: "./user.component.html",
  styleUrl: "./user.component.scss"
})
export class UserComponent {
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly userService: UserServiceInterface = inject(UserService);

  isUserDrawerOverflowing = signal(false);

  @ViewChild("userDetailsComponent")
  userDetailsComponent!: UserDetailsComponent;
  @ViewChild("userTableComponent")
  userTableComponent!: UserTableComponent;
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

  ngOnDestroy() {
    window.removeEventListener("resize", this.updateOverflowState);
  }

  updateOverflowState = () => {
    setTimeout(() => {
      this.isUserDrawerOverflowing.set(
        this.overflowService.isHeightOverflowing({
          selector: ".user-layout",
          thresholdSelector: ".drawer"
        })
      );
    }, 400);
  };
}
