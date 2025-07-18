import { Component, inject } from '@angular/core';
import { MatButton, MatIconButton } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatIcon } from '@angular/material/icon';
import { EnrollmentResponse } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../../services/content/content.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';
import { UserData } from '../../../../services/user/user.service';
import { TokenEnrollmentLastStepDialogComponent } from './token-enrollment-last-step-dialog.component';

export type TokenEnrollmentLastStepDialogData = {
  response: EnrollmentResponse;
  enrollToken: () => void;
  user: UserData | null;
  userRealm: string;
  onlyAddToRealm: boolean;
};

@Component({
  selector: 'app-token-enrollment-last-step-dialog-self-service',
  imports: [
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatIcon,
    MatIconButton,
  ],
  templateUrl:
    './token-enrollment-last-step-dialog.self-service.component.html',
  styleUrl: './token-enrollment-last-step-dialog.component.scss',
})
export class TokenEnrollmentLastStepDialogSelfServiceComponent extends TokenEnrollmentLastStepDialogComponent {
  protected override readonly Object = Object;
  protected override readonly dialogRef: MatDialogRef<TokenEnrollmentLastStepDialogComponent> =
    inject(MatDialogRef);
  public override readonly data: TokenEnrollmentLastStepDialogData =
    inject(MAT_DIALOG_DATA);
  protected override readonly tokenService: TokenServiceInterface =
    inject(TokenService);
  protected override readonly contentService: ContentServiceInterface =
    inject(ContentService);

  constructor() {
    super();
  }
}
