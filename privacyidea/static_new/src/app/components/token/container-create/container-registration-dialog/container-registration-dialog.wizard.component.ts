import { Component, Inject, WritableSignal } from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { ContainerRegistrationDialogComponent } from './container-registration-dialog.component';
import { AsyncPipe } from '@angular/common';
import { map } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer } from '@angular/platform-browser';
import { ContainerService } from '../../../../services/container/container.service';
import { LostTokenComponent } from '../../token-card/token-tab/lost-token/lost-token.component';

@Component({
  selector: 'app-container-registration-dialog',
  imports: [MatDialogContent, MatDialogTitle, AsyncPipe],
  templateUrl: './container-registration-dialog.wizard.component.html',
  styleUrl: './container-registration-dialog.component.scss',
})
export class ContainerRegistrationDialogWizardComponent extends ContainerRegistrationDialogComponent {
  readonly postTopHtml$ = this.http
    .get('/customize/container-create.wizard.post.top.html', {
      responseType: 'text',
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  readonly postBottomHtml$ = this.http
    .get('/customize/container-create.wizard.post.bottom.html', {
      responseType: 'text',
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer,
    containerService: ContainerService,
    dialogRef: MatDialogRef<LostTokenComponent>,
    @Inject(MAT_DIALOG_DATA)
    data: {
      response: any;
      containerSerial: WritableSignal<string>;
      selectedContent: WritableSignal<string>;
    },
  ) {
    super(containerService, dialogRef, data);
  }
}
