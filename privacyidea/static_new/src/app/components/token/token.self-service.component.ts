import { Component, inject } from '@angular/core';
import { TokenComponent } from './token.component';
import { MatCardModule } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatFabAnchor, MatFabButton } from '@angular/material/button';
import { ContainerCreateComponent } from './container-create/container-create.component';
import { ContainerDetailsComponent } from './container-details/container-details.component';
import { ContainerTableComponent } from './container-table/container-table.component';
import { TokenDetailsComponent } from './token-details/token-details.component';
import { TokenTableComponent } from './token-table/token-table.component';
import { VersionService } from '../../services/version/version.service';
import { TokenEnrollmentSelfServiceComponent } from './token-enrollment/token-enrollment.self-service.component';

@Component({
  selector: 'app-token-self-service',
  imports: [
    MatCardModule,
    MatIcon,
    MatFabAnchor,
    ContainerCreateComponent,
    ContainerDetailsComponent,
    ContainerTableComponent,
    TokenDetailsComponent,
    TokenEnrollmentSelfServiceComponent,
    TokenTableComponent,
    MatFabButton,
  ],
  templateUrl: './token.self-service.component.html',
  styleUrl: './token.component.scss',
})
export class TokenSelfServiceComponent extends TokenComponent {
  selectedContent = this.contentService.selectedContent;
  versionService = inject(VersionService);
}
