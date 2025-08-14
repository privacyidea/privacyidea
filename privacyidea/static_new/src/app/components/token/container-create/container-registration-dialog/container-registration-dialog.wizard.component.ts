import { AsyncPipe } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { Component, inject, WritableSignal } from "@angular/core";
import {
  MAT_DIALOG_DATA,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from "@angular/material/dialog";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import {
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { LostTokenComponent } from "../../token-card/token-tab/lost-token/lost-token.component";
import { ContainerRegistrationDialogComponent } from "./container-registration-dialog.component";

@Component({
  selector: "app-container-registration-dialog",
  imports: [MatDialogContent, MatDialogTitle, AsyncPipe],
  templateUrl: "./container-registration-dialog.wizard.component.html",
  styleUrl: "./container-registration-dialog.component.scss"
})
export class ContainerRegistrationDialogWizardComponent extends ContainerRegistrationDialogComponent {
  protected override readonly containerService: ContainerServiceInterface =
    inject(ContainerService);
  public override readonly data: {
    response: any;
    containerSerial: WritableSignal<string>;
  } = inject(MAT_DIALOG_DATA);

  readonly postTopHtml$ = this.http
    .get("/customize/container-create.wizard.post.top.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  readonly postBottomHtml$ = this.http
    .get("/customize/container-create.wizard.post.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer,
    dialogRef: MatDialogRef<LostTokenComponent>
  ) {
    super(dialogRef);
  }
}
