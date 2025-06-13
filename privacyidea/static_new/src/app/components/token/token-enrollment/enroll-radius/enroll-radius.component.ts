import {
  Component,
  computed,
  effect,
  Input,
  OnInit,
  Output,
  EventEmitter,
  WritableSignal,
} from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RadiusServerService } from '../../../../services/radius-server/radius-server.service';
import { SystemService } from '../../../../services/system/system.service';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface RadiusEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'radius';
  radiusServerConfiguration: string;
  radiusUser: string;
  checkPinLocally: boolean;
}

@Component({
  selector: 'app-enroll-radius',
  standalone: true,
  imports: [
    MatCheckbox,
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    ReactiveFormsModule,
    FormsModule,
    MatHint,
    MatError,
  ],
  templateUrl: './enroll-radius.component.html',
  styleUrl: './enroll-radius.component.scss',
})
export class EnrollRadiusComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'radius')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  radiusUserControl = new FormControl<string>(''); // Optional, depending on configuration
  radiusServerConfigurationControl = new FormControl<string>('', [
    Validators.required,
  ]);
  checkPinLocallyControl = new FormControl<boolean>(false, [
    Validators.required,
  ]);

  radiusForm = new FormGroup({
    radiusUser: this.radiusUserControl,
    radiusServerConfiguration: this.radiusServerConfigurationControl,
    checkPinLocally: this.checkPinLocallyControl,
  });

  radiusServerConfigurationOptions = computed(
    () =>
      this.radiusServerService
        .radiusServerConfigurations()
        ?.map((config) => config.name) ?? [],
  );

  defaultRadiusServerIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.['radius.identifier'];
  });

  constructor(
    private radiusServerService: RadiusServerService,
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {
    effect(() => {
      const id =
        this.systemService.systemConfigResource.value()?.result?.value?.[
          'radius.identifier'
        ];
      if (id && this.radiusServerConfigurationControl.pristine) {
        this.radiusServerConfigurationControl.setValue(id);
      }
    });
  }

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      radiusUser: this.radiusUserControl,
      radiusServerConfiguration: this.radiusServerConfigurationControl,
      checkPinLocally: this.checkPinLocallyControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.radiusForm.invalid) {
      this.radiusForm.markAllAsTouched();
      return undefined;
    }

    const enrollmentData: RadiusEnrollmentOptions = {
      ...basicOptions,
      type: 'radius',
      radiusUser: this.radiusUserControl.value ?? '',
      radiusServerConfiguration:
        this.radiusServerConfigurationControl.value ?? '',
      checkPinLocally: !!this.checkPinLocallyControl.value,
    };

    return this.tokenService.enrollToken(enrollmentData);
  };
}
