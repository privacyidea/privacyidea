import {
  Component,
  computed,
  Input,
  signal,
  WritableSignal,
} from '@angular/core';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatButton, MatIconButton } from '@angular/material/button';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
} from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import { FormsModule } from '@angular/forms';
import { VersionService } from '../../../services/version/version.service';
import { TokenSelectedContent } from '../token.component';
import { MatInput } from '@angular/material/input';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { distinctUntilChanged, from, switchMap } from 'rxjs';
import { map } from 'rxjs/operators';
import { UserService } from '../../../services/user/user.service';
import { RealmService } from '../../../services/realm/realm.service';
import { MatCheckbox } from '@angular/material/checkbox';
import { ContainerService } from '../../../services/container/container.service';

@Component({
  selector: 'app-container-create',
  imports: [
    MatButton,
    MatFormField,
    MatHint,
    MatIcon,
    MatOption,
    MatSelect,
    FormsModule,
    MatInput,
    MatLabel,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatError,
    MatCheckbox,
    MatIconButton,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
  ],
  templateUrl: './container-create.component.html',
  styleUrl: './container-create.component.scss',
})
export class ContainerCreateComponent {
  // TODO get this from container/types endpoint and add containerTypeOption interface
  containerTypes = [
    {
      key: 'generic',
      info: 'General prupose container that can hold any type and any number of token.',
      supportedToken: ['All'],
    },
    {
      key: 'smartphone',
      info: 'A smartphone that uses an authentication app.',
      supportedToken: ['Daypassword', 'HOTP', 'Push', 'SMS', 'TOTP'],
    },
    {
      key: 'yubikey',
      info: 'Yubikey hardware device that can hold HOTP, certificate and webauthn token.',
      supportedToken: [
        'Certificate',
        'HOTP',
        'Passkey',
        'Webauthn',
        'Yubico',
        'Yubikey',
      ],
    },
  ];
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() containerSerial!: WritableSignal<string>;
  description = signal('');
  selectedType = signal(this.containerTypes[0]);
  selectedUserRealm = signal('');
  selectedTemplate = signal('');
  realmOptions = signal<string[]>([]);
  templateOptions = signal<
    { container_type: string; default: boolean; name: string }[]
  >([]);
  selectedUsername = signal('');
  onlyAddToRealm = signal(false);
  generateQRCode = signal(false);
  fetchedUsernames = toSignal(
    toObservable(this.selectedUserRealm).pipe(
      distinctUntilChanged(),
      switchMap((realm) => {
        if (!realm) {
          return from<string[]>([]);
        }
        return this.userService
          .getUsers(realm)
          .pipe(
            map((result: any) =>
              result.value.map((user: any) => user.username),
            ),
          );
      }),
    ),
    { initialValue: [] },
  );
  userOptions = computed(() => this.fetchedUsernames());
  filteredUserOptions = computed(() => {
    const filterValue = (this.selectedUsername() || '').toLowerCase();
    return this.userOptions().filter((option: any) =>
      option.toLowerCase().includes(filterValue),
    );
  });
  passphrasePrompt = signal('');
  passphraseResponse = signal('');

  constructor(
    protected versioningService: VersionService,
    private userService: UserService,
    private realmService: RealmService,
    private containerService: ContainerService,
  ) {}

  ngAfterViewInit() {
    this.getRealmOptions();
    this.getTemplateOptions();
  }

  getTemplateOptions() {
    this.containerService.getTemplates().subscribe({
      next: (templates: any) => {
        this.templateOptions.set(templates.result.value.templates);
      },
    });
  }

  getRealmOptions() {
    this.realmService.getRealms().subscribe({
      next: (realms: any) => {
        this.realmOptions.set(Object.keys(realms.result.value));
      },
    });
  }

  createContainer() {
    this.containerService
      .createContainer({
        container_type: this.selectedType().key,
        description: this.description(),
        serial: this.containerSerial(),
        user_realm: this.selectedUserRealm(),
        template: this.selectedTemplate(),
        user: this.selectedUsername(),
        realm: this.onlyAddToRealm() ? this.selectedUserRealm() : '',
        passphrase_prompt: this.passphrasePrompt(),
        passphrase_response: this.passphraseResponse(),
      })
      .subscribe({
        next: (response: any) => {
          this.selectedContent.set('container_details');
          this.containerSerial.set(response.result.value.container_serial);
        },
      });
  }
}
