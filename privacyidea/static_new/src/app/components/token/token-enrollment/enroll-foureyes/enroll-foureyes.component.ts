import {
  Component,
  computed,
  Input,
  OnInit,
  Output,
  EventEmitter,
  Signal,
  WritableSignal,
} from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RealmService } from '../../../../services/realm/realm.service';
import {
  ErrorStateMatcher,
  MatOption,
  MatOptionSelectionChange,
} from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import { MatCheckbox } from '@angular/material/checkbox';
import {
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';

import { Observable, of } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { FourEyesApiPayloadMapper } from '../../../../mappers/token-api-payload/4eyes-token-api-payload.mapper';

export interface FourEyesEnrollmentOptions extends TokenEnrollmentData {
  type: '4eyes';
  separator: string;
  requiredTokenOfRealms: { realm: string; tokens: number }[];
  onlyAddToRealm: boolean;
  userRealm?: string; // Optional, only if onlyAddToRealm is true
}

export class RequiredRealmsErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid =
      control && control.value ? control.value.length === 0 : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: 'app-enroll-foureyes',
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatOption,
    MatSelect,
    MatCheckbox,
    MatError,
  ],
  templateUrl: './enroll-foureyes.component.html',
  styleUrl: './enroll-foureyes.component.scss',
})
export class EnrollFoureyesComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === '4eyes')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  separatorControl = new FormControl<string>(':', [Validators.required]);
  requiredTokensOfRealmsControl = new FormControl<
    { realm: string; tokens: number }[]
  >([], [Validators.required, Validators.minLength(1)]);
  onlyAddToRealmControl = new FormControl<boolean>(false, [
    Validators.required,
  ]);
  // userRealmControl is needed if onlyAddToRealm is true,
  // but this value comes from the parent component (userService.selectedUserRealm)
  // and is passed in basicOptions.

  foureyesForm = new FormGroup({
    separator: this.separatorControl,
    requiredTokensOfRealms: this.requiredTokensOfRealmsControl,
    onlyAddToRealm: this.onlyAddToRealmControl,
  });

  // Options for the template
  realmOptions = this.realmService.realmOptions;
  tokenCountMapping: Signal<Record<string, number>> = computed(() => {
    const realms = this.requiredTokensOfRealmsControl.value;
    if (!realms) {
      return {};
    }
    return realms.reduce(
      (acc, curr) => {
        acc[curr.realm] = curr.tokens;
        return acc;
      },
      {} as Record<string, number>,
    );
  });
  requiredRealmsErrorStateMatcher = new RequiredRealmsErrorStateMatcher();

  constructor(
    private realmService: RealmService,
    private tokenService: TokenService,
    private enrollmentMapper: FourEyesApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      separator: this.separatorControl,
      requiredTokensOfRealms: this.requiredTokensOfRealmsControl,
      onlyAddToRealm: this.onlyAddToRealmControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  getTokenCount(realm: string): number {
    const tokensArray = this.requiredTokensOfRealmsControl.value;
    if (!tokensArray) return 0;
    const tokenObj = tokensArray.find((item) => item.realm === realm);
    return tokenObj ? tokenObj.tokens : 0;
  }

  updateTokenCount(realm: string, tokens: number): void {
    let tokensArray = this.requiredTokensOfRealmsControl.value;
    if (!tokensArray) tokensArray = [];

    const index = tokensArray.findIndex((item) => item.realm === realm);
    if (index > -1) {
      if (tokens === 0) {
        // Remove if count is 0
        tokensArray.splice(index, 1);
      } else {
        tokensArray[index] = { realm, tokens };
      }
    } else {
      if (tokens > 0) {
        // Add only if count is > 0
        tokensArray.push({ realm, tokens });
      }
    }
    this.requiredTokensOfRealmsControl.setValue([...tokensArray]);
    this.requiredTokensOfRealmsControl.markAsDirty();
    this.requiredTokensOfRealmsControl.updateValueAndValidity();
  }

  onRealmSelectionChange(event: MatOptionSelectionChange, realm: string): void {
    if (event.isUserInput && event.source.selected) {
      if (this.getTokenCount(realm) === 0) {
        this.updateTokenCount(realm, 1);
      }
    } else if (event.isUserInput && !event.source.selected) {
      this.updateTokenCount(realm, 0); // Remove from selection
    }
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    if (this.foureyesForm.invalid) {
      this.foureyesForm.markAllAsTouched();
      return of(null);
    }
    const enrollmentData: FourEyesEnrollmentOptions = {
      ...basicOptions,
      type: '4eyes',
      separator: this.separatorControl.value ?? ':',
      requiredTokenOfRealms: this.requiredTokensOfRealmsControl.value ?? [],
      onlyAddToRealm: !!this.onlyAddToRealmControl.value,
      // userRealm wird von basicOptions übernommen, falls onlyAddToRealm true ist
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
